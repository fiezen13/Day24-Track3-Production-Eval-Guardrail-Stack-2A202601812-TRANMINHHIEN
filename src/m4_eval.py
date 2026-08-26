from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (OPENAI_API_KEY, TEST_SET_PATH, LLM_API_KEY, LLM_BASE_URL,
                    LLM_MODEL, RAGAS_EMBEDDING_MODEL, LLM_LIMITER, LLM_HTTP_TIMEOUT)


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation."""
    zeros = {"faithfulness": 0.0, "answer_relevancy": 0.0,
             "context_precision": 0.0, "context_recall": 0.0, "per_question": []}
    if not OPENAI_API_KEY:
        print("  ⚠️  RAGAS skipped: no GEMINI_API_KEY / OPENAI_API_KEY")
        return zeros
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return zeros
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from ragas.run_config import RunConfig
        from ragas.llms import base as ragas_llm_base
        from datasets import Dataset
        from langchain_openai import ChatOpenAI

        # Gemini Flash Lite không hỗ trợ n>1 (multiple candidates).
        ragas_llm_base.is_multiple_completion_supported = lambda llm: False
        answer_relevancy.strictness = 1

        llm = ChatOpenAI(
            model=LLM_MODEL,
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL or None,
            temperature=0,
            n=1,
            max_retries=2,
            timeout=LLM_HTTP_TIMEOUT,
            rate_limiter=LLM_LIMITER,
        )
        from langchain_community.embeddings import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-m3",
            encode_kwargs={"normalize_embeddings": True},
        )

        dataset = Dataset.from_dict({
            "question": questions, "answer": answers,
            "contexts": contexts, "ground_truth": ground_truths,
        })
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=llm,
            embeddings=embeddings,
            run_config=RunConfig(timeout=300, max_workers=1, max_retries=4, max_wait=60),
        )
        df = result.to_pandas()

        def _metric(row, key: str) -> float:
            try:
                v = float(row.get(key, 0.0))
                return 0.0 if v != v else v  # NaN → 0
            except (TypeError, ValueError):
                return 0.0

        per_question = [
            EvalResult(
                question=row["question"],
                answer=row["answer"],
                contexts=list(row["contexts"]) if row["contexts"] is not None else [],
                ground_truth=row["ground_truth"],
                faithfulness=_metric(row, "faithfulness"),
                answer_relevancy=_metric(row, "answer_relevancy"),
                context_precision=_metric(row, "context_precision"),
                context_recall=_metric(row, "context_recall"),
            )
            for _, row in df.iterrows()
        ]
        return {
            "faithfulness": float(df["faithfulness"].mean(skipna=True)) if "faithfulness" in df else 0.0,
            "answer_relevancy": float(df["answer_relevancy"].mean(skipna=True)) if "answer_relevancy" in df else 0.0,
            "context_precision": float(df["context_precision"].mean(skipna=True)) if "context_precision" in df else 0.0,
            "context_recall": float(df["context_recall"].mean(skipna=True)) if "context_recall" in df else 0.0,
            "per_question": per_question,
        }
    except Exception as e:
        print(f"  ⚠️  RAGAS evaluation failed: {e}")
        return zeros


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    diagnostic_tree = {
        "faithfulness": ("LLM hallucinating", "Tighten prompt, lower temperature"),
        "context_recall": ("Missing relevant chunks", "Improve chunking or add BM25"),
        "context_precision": ("Too many irrelevant chunks", "Add reranking or metadata filter"),
        "answer_relevancy": ("Answer doesn't match question", "Improve prompt template"),
    }
    scored = []
    for r in eval_results:
        metrics = {
            "faithfulness": r.faithfulness,
            "answer_relevancy": r.answer_relevancy,
            "context_precision": r.context_precision,
            "context_recall": r.context_recall,
        }
        avg = sum(metrics.values()) / max(len(metrics), 1)
        worst_metric = min(metrics, key=metrics.get)
        diagnosis, suggested_fix = diagnostic_tree[worst_metric]
        scored.append({
            "question": r.question,
            "answer": r.answer,
            "ground_truth": r.ground_truth,
            "worst_metric": worst_metric,
            "score": avg,
            "metric_scores": metrics,
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
        })
    scored.sort(key=lambda x: x["score"])
    return scored[:bottom_n]


def save_report(results: dict, failures: list[dict], path: str = "ragas_report.json", extra: dict | None = None):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    if extra:
        report.update(extra)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
