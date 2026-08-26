"""Shared configuration for Lab 24: Eval + Guardrail Stack."""

import os
import threading
import time
from dotenv import load_dotenv
from langchain_core.rate_limiters import BaseRateLimiter

load_dotenv()

# --- API Keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")  # Optional: for HuggingFace models
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

LLM_RPM = int(os.getenv("LLM_RPM", "4"))
LLM_HTTP_TIMEOUT = 60.0
LLM_ENRICH = os.getenv("LLM_ENRICH", "0").lower() in ("1", "true", "yes")

# Prefer real OpenAI (sk-...) for Lab 24 judge + NeMo.
# Gemini keys (often AQ....) must use the OpenAI-compatible Gemini base_url.
_real_openai = bool(OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-"))
_gemini_key = GEMINI_API_KEY or (
    OPENAI_API_KEY if OPENAI_API_KEY and not OPENAI_API_KEY.startswith("sk-") else ""
)

if _real_openai:
    LLM_API_KEY = OPENAI_API_KEY
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    RAGAS_EMBEDDING_MODEL = os.getenv("RAGAS_EMBEDDING_MODEL", "text-embedding-3-small")
elif _gemini_key:
    LLM_API_KEY = _gemini_key
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", GEMINI_BASE_URL)
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")
    RAGAS_EMBEDDING_MODEL = os.getenv("RAGAS_EMBEDDING_MODEL", "gemini-embedding-001")
    OPENAI_API_KEY = _gemini_key
else:
    LLM_API_KEY = ""
    LLM_BASE_URL = ""
    LLM_MODEL = "gpt-4o-mini"
    RAGAS_EMBEDDING_MODEL = "text-embedding-3-small"

if LLM_API_KEY:
    os.environ.setdefault("OPENAI_API_KEY", LLM_API_KEY)
if LLM_BASE_URL:
    # So any library that reads OpenAI env (RAGAS internals) hits Gemini, not api.openai.com
    os.environ["OPENAI_BASE_URL"] = LLM_BASE_URL
    os.environ["OPENAI_API_BASE"] = LLM_BASE_URL


class RpmLimiter(BaseRateLimiter):
    """Serialize calls so we stay under provider RPM."""

    def __init__(self, rpm: int = 10, extra_delay: float = 0.6):
        self.min_interval = 60.0 / max(rpm, 1) + extra_delay
        self._lock = threading.Lock()
        self._last = 0.0

    def acquire(self, *, blocking: bool = True) -> bool:
        with self._lock:
            now = time.monotonic()
            wait = self.min_interval - (now - self._last)
            if wait > 0:
                if not blocking:
                    return False
                time.sleep(wait)
            self._last = time.monotonic()
            return True

    async def aacquire(self, *, blocking: bool = True) -> bool:
        return self.acquire(blocking=blocking)


LLM_LIMITER = RpmLimiter(rpm=LLM_RPM, extra_delay=1.0)


def get_openai_client():
    """OpenAI SDK client — Gemini via OpenAI-compatible base_url when needed."""
    from openai import OpenAI

    kwargs = {"api_key": LLM_API_KEY, "max_retries": 2, "timeout": LLM_HTTP_TIMEOUT}
    if LLM_BASE_URL:
        kwargs["base_url"] = LLM_BASE_URL
    client = OpenAI(**kwargs)
    original = client.chat.completions.create

    def throttled_create(*args, **kwargs):
        last_err = None
        for attempt in range(6):
            LLM_LIMITER.acquire()
            try:
                return original(*args, **kwargs)
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                if "free_tier_requests" in msg and "quotaid" in msg.replace(" ", "").lower():
                    print("  ⚠️  Daily quota exhausted for this model — stop retrying", flush=True)
                    raise
                if "429" in msg or "rate" in msg or "resource_exhausted" in msg or "quota" in msg:
                    wait = 30 * (attempt + 1)
                    print(f"  ⚠️  LLM 429/rate-limit, backoff {wait}s (attempt {attempt + 1}/6)", flush=True)
                    time.sleep(wait)
                    continue
                raise
        raise last_err

    client.chat.completions.create = throttled_create
    return client


# --- Qdrant (same as Day 18) ---
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "lab24_production"

# --- Embedding (same as Day 18) ---
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

# --- Chunking (same as Day 18) ---
HIERARCHICAL_PARENT_SIZE = 2048
HIERARCHICAL_CHILD_SIZE = 256
SEMANTIC_THRESHOLD = 0.85

# --- Search (same as Day 18) ---
BM25_TOP_K = 20
DENSE_TOP_K = 20
HYBRID_TOP_K = 20
RERANK_TOP_K = 3

# --- Paths ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TEST_SET_PATH = os.path.join(os.path.dirname(__file__), "test_set_50q.json")
ANSWERS_PATH = os.path.join(os.path.dirname(__file__), "answers_50q.json")
HUMAN_LABELS_PATH = os.path.join(os.path.dirname(__file__), "human_labels_10q.json")
ADVERSARIAL_SET_PATH = os.path.join(os.path.dirname(__file__), "adversarial_set_20.json")
GUARDRAILS_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "guardrails")

# --- LLM Judge ---
JUDGE_MODEL = os.getenv("JUDGE_MODEL", LLM_MODEL if LLM_MODEL else "gpt-4o-mini")

# --- Guardrail latency budget ---
LATENCY_BUDGET_P95_MS = 500  # target: full guard stack P95 < 500ms
PRESIDIO_LANGUAGE = "en"    # Presidio base language; custom VN recognizers added via PatternRecognizer
