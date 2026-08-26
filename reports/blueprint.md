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
    ▼ (~1.83ms P95)
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
**Comment:** Guard P95 ~8ms << 500ms. Bottleneck production là RAG (embedding + LLM), không phải Presidio/NeMo keyword rails.

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
| RAGAS avg_score (50q) | factual 0.905 / multi_hop 0.640 / adversarial 0.785 |
| Worst metric | context_precision trên multi_hop (0.475) |
| Dominant failure distribution | factual (worst-count) / multi_hop (avg thấp nhất) |
| Cohen's κ | 1.000 |
| Adversarial pass rate | 20 / 20 |
| Guard P95 latency | 7.88 ms |

---

## Nhận xét & Cải tiến

> Presidio bắt tốt VN_CCCD/VN_PHONE; lọc DATE_TIME tránh false positive ("năm 2024").  
> NeMo + keyword pre-filter đạt 20/20 adversarial; bổ sung intent embedding khi attack mới.  
> LLM-as-judge κ=1.0 khi neo ground_truth; bắt buộc swap-and-average (position bias ~40%).  
> Deploy: metadata filter theo version policy (v2024) để giảm version conflict.  
> Guard latency không bottleneck — ưu tiên tối ưu multi_hop retrieval (rerank, chunk overlap).
