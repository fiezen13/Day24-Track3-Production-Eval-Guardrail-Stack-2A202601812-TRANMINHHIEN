# Failure Cluster Analysis — Phase A

**Sinh viên:** Tran Minh Hien  
**Ngày:** 2026-08-26

---

## 1. Aggregate RAGAS Scores theo Distribution

| Metric | factual | multi_hop | adversarial |
|---|---|---|---|
| faithfulness | 0.933 | 0.710 | 0.950 |
| answer_relevancy | 0.863 | 0.753 | 0.831 |
| context_precision | 0.975 | 0.475 | 0.708 |
| context_recall | 0.850 | 0.621 | 0.650 |
| **avg_score** | **0.905** | **0.640** | **0.785** |

---

## 2. Bottom 10 Questions

| Rank | Distribution | Question | avg_score | worst_metric |
|---|---|---|---|---|
| 1 | multi_hop | Manager 12 năm: phụ cấp + phép năm v2024? | 0.125 | faithfulness |
| 2 | factual | Mua thiết bị 55 triệu cần ai phê duyệt? | 0.250 | faithfulness |
| 3 | multi_hop | Kết hôn + con kết hôn cùng tuần: tổng ngày nghỉ? | 0.333 | answer_relevancy |
| 4 | multi_hop | Thâm niên 7 năm + trừ 4 ngày ốm: còn bao nhiêu phép? | 0.408 | context_recall |
| 5 | multi_hop | Laptop 30 triệu: ai phê duyệt + cần gì từ CNTT? | 0.435 | context_precision |
| 6 | multi_hop | So sánh mật khẩu v1.0 vs v2.0 | 0.475 | context_precision |
| 7 | multi_hop | Tự xóa malware + share Slack: vi phạm gì? | 0.481 | context_precision |
| 8 | adversarial | Theo v2023 nghỉ bao nhiêu ngày? Policy hiện hành? | 0.540 | context_precision |
| 9 | multi_hop | So sánh BH thử việc vs chính thức | 0.603 | context_precision |
| 10 | multi_hop | Thử việc T3 phát hiện vi phạm bảo mật: nên/không nên? | 0.623 | context_precision |

---

## 3. Failure Cluster Matrix

*(Mỗi ô = số câu có worst_metric = row, thuộc distribution = col)*

| worst_metric | factual | multi_hop | adversarial | Total |
|---|---|---|---|---|
| faithfulness | 2 | 4 | 1 | 7 |
| answer_relevancy | 13 | 5 | 1 | 19 |
| context_precision | 2 | 8 | 5 | 15 |
| context_recall | 3 | 3 | 3 | 9 |

---

## 4. Dominant Failure Analysis

**Dominant distribution:** factual (theo số câu có worst_metric; nhưng **avg thấp nhất là multi_hop 0.640**)  
**Dominant metric:** answer_relevancy

**Lý do phân tích:**

> Factual có nhiều câu “worst = answer_relevancy” dù avg vẫn cao (0.90) — metric tương đối yếu hơn 3 metric còn lại trên câu tra cứu đơn giản.  
> Multi_hop mới là điểm yếu thực sự: context_precision 0.475 vì cần ghép nhiều tài liệu (phép + phụ cấp + phê duyệt).  
> Adversarial avg 0.785 < factual 0.905 → test set đang stress-test đúng (bonus).  
> Bottom-10 chủ yếu multi_hop; 1 adversarial về v2023/v2024 cho thấy version conflict trong corpus.

---

## 5. Suggested Fixes

| Metric yếu | Root cause | Suggested fix |
|---|---|---|
| faithfulness | LLM hallucinating | Siết system prompt, temperature=0, cite chunk |
| context_recall | Missing relevant chunks | Cải thiện chunking / tăng BM25 weight |
| context_precision | Too many irrelevant chunks | Rerank mạnh hơn + metadata filter theo version |
| answer_relevancy | Answer doesn't match question | Cải thiện prompt template, yêu cầu trả lời đúng câu hỏi |

---

## 6. Nhận xét về Adversarial Distribution

> avg adversarial (0.785) thấp hơn factual (0.905) — pipeline bị stress bởi version conflict.  
> Câu #8 bottom-10 hỏi v2023 vs hiện hành: corpus có cả nghi_phep v2023 và v2024 nên retrieval lẫn context.  
> Fix production: filter metadata `version=current` / `effective_date` trước khi generate.  
> Multi_hop kém hơn adversarial về avg → ưu tiên cải retrieval cross-doc trước jailbreak-style traps.
