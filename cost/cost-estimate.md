# Chi phí khi dùng thật

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Ôn lại: ngày 13, ngày 1, ngày 14 · lab ngày 13, lab ngày 14. Chấm ở rubric R6.
> Số **không điền tay**: điền `cost/personas.yaml` → `python run.py simulate` → chép bảng trong `cost/simulate-N-summary.md` vào đây.
> Lúc build dùng gói miễn phí vẫn tính theo **giá gói trả phí** — đây là chi phí cho lúc đưa vào dùng thật.

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): 3 kiểu theo tần suất đặt hộ — `dat_it` 59% (1,5 phiên/người/tháng, 1 lượt/phiên), `dat_vua` 32% (4,0 phiên, 2 lượt), `dat_nhieu` 9% (10,4 phiên, 3 lượt). Nguồn: tỉ lệ và số phiên từ Q2 khảo sát `evidence/survey/results_valid.csv` (n = 56); số lượt/phiên *(tự ước tính theo Pipeline 8 bước: dựng giỏ / hỏi bù / quay xe)*.
- **Số người dùng thật** 3 kịch bản: thấp 50 · cơ sở 100 · cao 200 người đặt hộ. Nguồn: *(tự ước tính)*, khớp `spec.md` §2.
- **Giá** 3 mức model (USD / 1M token, giá trả phí): `deepseek/deepseek-v4.1-flash` vào 0,051 · ra 0,567 ([OpenRouter](https://openrouter.ai/deepseek/deepseek-v4.1-flash), xem 28/11/2026) · `gemini-2.5-flash` vào 0,30 · ra 2,50 ([Google AI](https://ai.google.dev/gemini-api/docs/pricing), xem 28/11/2026) · `google/gemini-4-hydrogen` vào 1,50 · ra 7,50 ([OpenRouter](https://openrouter.ai/google/gemini-4-hydrogen), xem 28/11/2026).
- **Tỉ lệ đạt** dùng để tính: 26/27 (96%) — lượt `run-6@20261128-121103` (lượt 2, xem `eval/report.md` mục 5).
- Đo token trên model `deepseek/deepseek-v4.1-flash`, tính giá cho cả `deepseek/deepseek-v4.1-flash`, `gemini-2.5-flash` và `google/gemini-4-hydrogen` (model khác bộ tách token → số token thật có thể lệch).

## 2. Kết quả mô phỏng

Lượt mô phỏng: `cost/simulate-1.csv` · run ID `simulate-1@20261128-121751` · 50 phiên · seed 42 · 0/50 phiên lỗi · trace `traces/simulate-1.jsonl`

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| dat_it | 33 | 1 | 1199 | 381 | 1.5 | 1.6 |
| dat_vua | 15 | 2 | 2203 | 783 | 2.9 | 3.1 |
| dat_nhieu | 2 | 3 | 2834 | 1158 | 3.5 | 5.5 |

| Model | Chi phí / phiên | Chi phí / task thành công | / tháng — thấp (50) | / tháng — cơ sở (100) | / tháng — cao (200) | / người / tháng (cơ sở) |
|---|---|---|---|---|---|---|
| deepseek/deepseek-v4.1-flash | $0.00038 | $0.00040 | $0.0854 | $0.1708 | $0.3416 | $0.0017 |
| gemini-2.5-flash | $0.0018 | $0.0019 | $0.4010 | $0.8021 | $1.60 | $0.0080 |
| google/gemini-4-hydrogen | $0.0063 | $0.0066 | $1.40 | $2.80 | $5.60 | $0.0280 |

Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt (96%) — **không coi như đạt 100%**.

## 3. So với impact

- Impact / người / tháng (`spec.md` §2): tiết kiệm kỳ vọng **~19,7 phút / người đặt hộ / tháng** (39,4 phút gom đơn hiện tại × mục tiêu giảm 50%, *(tự ước tính)*).
- Chi phí / người / tháng (cơ sở, model `deepseek/deepseek-v4.1-flash`): **$0.0017** (≈ $0.17 / tháng cho cả 100 người); ngay cả model đắt nhất trong bảng (`google/gemini-4-hydrogen`) cũng chỉ **$0.028 / người / tháng**.
- **Kết luận một dòng — đáng làm không:** Đáng làm — chi phí model dưới 3 cent / người / tháng ở mọi mức giá, rất nhỏ so với ~20 phút tiết kiệm mỗi tháng; rủi ro thật nằm ở độ đúng (dị ứng, ngân sách) chứ không ở tiền model, nên ưu tiên model rẻ đã đo (`deepseek/deepseek-v4.1-flash`) và giữ kiểm tra bằng Python.

## 4. *(Muốn sâu hơn, không bắt buộc)*

- Bảng độ nhạy: chênh giữa model rẻ nhất và đắt nhất ~16,5× chi phí / phiên ($0.00038 → $0.0063). Fast-path (bỏ lần gọi model thứ 2 khi mỗi người chỉ còn 1 ứng viên) và payload chọn món rút gọn đã giảm token vào ~24% giữa lượt 1 và lượt 2 (`eval/report.md` mục 5).
- Chi phí ngoài model: chạy cục bộ (SQLite, không hosting) trong bản thử; giờ công người duyệt giỏ là chi phí chính và đã nằm trong thời gian gom đơn ở §2.
- Quy mô: chi phí model tăng tuyến tính theo số người; ở 200 người vẫn < $6 / tháng với model đắt nhất trong bảng.
