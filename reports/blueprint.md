# CI/CD Blueprint: RAG Eval + Guardrail Stack

**Sinh viên:** Tran Minh Hien  
**Ngày:** 2026-08-26

---

## Guard Stack Architecture

```
User Input
    │
    ▼ (~6.56ms P95)
[Presidio PII Scan]
    │ block if: VN_CCCD / VN_PHONE / EMAIL detected
    │ action:   return 400 + "PII detected in query"
    ▼ (~1.83ms P95 — Colang keyword + NeMo rails)
[NeMo Input Rail]
    │ block if: off-topic / jailbreak / prompt injection
    │ action:   return 503 + refuse message
    ▼
[RAG Pipeline (Day 18)]
    │ M1 Chunk → M2 Search → M3 Rerank → LLM
    ▼
[NeMo Output Rail]
    │ flag if:  PII in response / sensitive content
    │ action:   replace with safe response
    ▼
User Response
```

---

## Latency Budget

*(Từ kết quả Task 12 — measure_p95_latency())*

| Layer | P50 (ms) | P95 (ms) | P99 (ms) | Budget |
|---|---|---|---|---|
| Presidio PII | 5.58 | 6.56 | 6.56 | <10ms |
| NeMo Input Rail | 1.00 | 1.83 | 1.83 | <300ms |
| RAG Pipeline | ~2000 | ~3000 | ~5000 | <2000ms |
| NeMo Output Rail | ~1 | ~2 | ~2 | <300ms |
| **Total Guard** | 6.49 | **7.88** | 7.88 | **<500ms** |

**Budget OK?** [x] Yes / [ ] No  
**Comment:** Guard stack P95 ~8ms << 500ms. Bottleneck production vẫn là RAG (embedding + LLM), không phải Presidio/NeMo keyword rails. Khi NeMo gọi LLM thật (không match Colang), latency sẽ tăng ~200–800ms — cần cache intent hoặc small classifier.

---

## CI/CD Gates (phải pass trước khi merge to main)

```yaml
# .github/workflows/rag_eval.yml
- name: RAGAS Quality Gate
  run: python src/phase_a_ragas.py
  env:
    MIN_FAITHFULNESS: 0.75
    MIN_AVG_SCORE: 0.65

- name: Guardrail Gate
  run: pytest tests/test_phase_c.py -k "test_adversarial_suite_pass_rate"
  # phải ≥ 15/20 (75%); lab đạt 20/20

- name: Latency Gate
  run: python -c "from src.phase_c_guard import measure_p95_latency; ..."
  # P95 total < 500ms
```

---

## Monitoring Dashboard (production)

| Metric | Alert Threshold | Action |
|---|---|---|
| RAGAS faithfulness (daily sample) | < 0.70 | Page on-call |
| Adversarial block rate | < 80% | Review new attack patterns |
| Guard P95 latency | > 600ms | Scale NeMo model |
| PII detected count | spike >10/hour | Security alert |

---

## Kết quả thực tế từ Lab

| | Kết quả |
|---|---|
| RAGAS avg_score (50q) | (đang chạy — điền sau Phase A) |
| Worst metric | (đang chạy — điền sau Phase A) |
| Dominant failure distribution | (đang chạy — điền sau Phase A) |
| Cohen's κ | 1.000 |
| Adversarial pass rate | 20 / 20 |
| Guard P95 latency | 7.88 ms |

---

## Nhận xét & Cải tiến

> Presidio bắt tốt VN_CCCD/VN_PHONE; cần lọc DATE_TIME để tránh false positive trên "năm 2024".  
> NeMo Colang + keyword pre-filter đạt 20/20 adversarial; nên bổ sung embedding-based intent khi attack mới xuất hiện.  
> LLM-as-judge đạt κ=1.0 khi neo ground_truth; bắt buộc swap-and-average vì position bias ~40%.  
> Deploy thật: metadata filter theo version policy (v2024) để giảm adversarial failure từ version conflict trong corpus.  
> Guard latency không phải bottleneck — tối ưu RAG (rerank top-k, cache embedding) mang lại ROI cao hơn.
