# LLM Judge Bias Report — Phase B

**Sinh viên:** Tran Minh Hien  
**Ngày:** 2026-08-26  
**Judge model:** gemini-3.1-flash-lite (Gemini OpenAI-compatible; fallback khi chưa có OpenAI key)

---

## 1. Pairwise Judge Results

*(Chạy pairwise_judge() / swap_and_average trên 5 cặp answers)*

| # | Question (tóm tắt) | Winner | Reasoning tóm tắt |
|---|---|---|---|
| 1 | Ngày phép năm? | tie (sau swap) | Pass1 tie; Pass2 nghiêng A (15 ngày v2024) — position inconsistent |
| 2 | Thưởng Tết tối thiểu? | tie | Pass1 chọn A (1 tháng lương); Pass2 lệch → tie |
| 3 | Thử việc có phép năm? | A | A đúng: không được phép năm, xin nghỉ không lương |
| 4 | VPN cá nhân khi WFH? | A | A đúng: cấm VPN cá nhân, dùng WireGuard công ty |
| 5 | Mua thiết bị 55tr? | A | A đúng: >50tr cần CEO phê duyệt |

---

## 2. Swap-and-Average Results

| # | Pass 1 Winner | Pass 2 Winner | Final | Position Consistent? |
|---|---|---|---|---|
| 1 | tie | A | tie | No |
| 2 | A | tie | tie | No |
| 3 | A | A | A | Yes |
| 4 | A | A | A | Yes |
| 5 | A | A | A | Yes |

**Position bias rate:** 40% (= 2/5 case NOT consistent)

---

## 3. Cohen's κ Analysis

**Human labels:** `human_labels_10q.json` (10 câu, 5 label=1, 5 label=0)  
**Judge labels:** chạy `_judge_binary_label` so với ground_truth

| Question ID | Human Label | Judge Label | Agree? |
|---|---|---|---|
| 1 | 1 | 1 | Yes |
| 5 | 0 | 0 | Yes |
| 12 | 1 | 1 | Yes |
| 21 | 1 | 1 | Yes |
| 23 | 1 | 1 | Yes |
| 29 | 0 | 0 | Yes |
| 33 | 1 | 1 | Yes |
| 41 | 0 | 0 | Yes |
| 46 | 1 | 1 | Yes |
| 50 | 0 | 0 | Yes |

**Cohen's κ:** 1.000  
**Interpretation:** almost perfect (Landis–Koch > 0.8)

---

## 4. Verbosity Bias

Trong các case có winner rõ ràng (không phải tie):
- A thắng + A dài hơn B: 2 / 2 cases
- B thắng + B dài hơn A: 0 / 2 cases  
- **Verbosity bias rate:** 100%

**Kết luận:** Trên sample nhỏ (2 decisive), judge chọn answer dài hơn khi A thắng. Cần swap-and-average và sample lớn hơn trước khi dùng làm gate production.

---

## 5. Nhận xét chung

> κ = 1.0 trên 10 nhãn human — LLM judge neo ground_truth đạt mức almost perfect, đủ tin cậy cho bonus (>0.6).  
> Position bias 40% cho thấy thứ tự A/B ảnh hưởng kết quả; swap-and-average là bắt buộc.  
> Verbosity bias cao trên sample nhỏ — production nên chuẩn hóa độ dài hoặc thêm tiêu chí súc tích có trọng số.  
> Nên chạy judge trên batch cố định + lưu seed/model version để audit.
