# Báo cáo Kiểm toán Chất lượng Dữ liệu (`vibe-data`)

- **Tệp kiểm toán:** `data/processed/vietnamese_dishes.csv`
- **Nguồn gốc xác minh (Provenance):**
  - Repository: `https://github.com/QuocAn55/A-New-Dataset-and-Empirical-Evaluation-for-Vietnamese-Food-Recommendation-System`
  - Branch / Commit SHA: `main` · `126caa3a8b58708a09b2b2e119ff4923b6f06d82` (`2024-03-14`)
  - File đầu vào trong repo gốc: `Data/Clean Dataset/foods.csv` (4.000 dòng) + `Data/Raw Dataset/food_dataset_mnmnweb.csv` (1.213 dòng)
  - Đối chiếu dinh dưỡng thật: `thanhphuong080199/foodscan-vn` (`MIT` — số hóa từ Bảng Thành phần Thực phẩm Việt Nam, Viện Dinh dưỡng Quốc gia)
- **Ngày chạy kiểm toán:** 2026-11-27
- **Script làm sạch cục bộ (không crawl web):** `scripts/build_vietnamese_dishes_csv.py`

## 1. Kết quả kiểm toán CLI (`data-probe` + `data-text`)

| Chỉ số kiểm toán | Giá trị đo thực tế | Trạng thái |
|---|---:|---|
| Tổng số món ăn sạch (`total_records`) | 3.732 | Đạt |
| Bản ghi bị lọc bỏ (món ngoại / trùng lặp / thiếu thành phần) | `107 / 158 / 3` | Đã lọc |
| Bản ghi rỗng (`empty_records`) | 0 | Đạt |
| Nhiễu ngắn `< 4 từ` (`short_noise_records`) | 0 | Đạt |
| Lỗi bảng mã không phải Unicode NFC (`non_nfc_records`) | 0 | Đạt |
| Rác BOM / Null bytes (`control_or_bom_records`) | 0 | Đạt |
| Thẻ HTML còn sót (`html_artifact_records`) | 0 | Đạt |
| Lỗi hỏng chữ `muỗngl` / `muỗngiếng` còn sót | 0 | Đạt |
| Trùng lặp tuyệt đối & gần giống (`exact` / `near` / `shingle`) | `0 / 0 / 0` | Đạt |
| Độ dài cột `thanh_phan` (word count: `min / p25 / median / p95 / max`) | `4 / 29 / 41 / 77 / 133` | Đạt |
| Ước lượng token cột `thanh_phan` (`min / p25 / median / p95 / max`) | `5 / 39 / 55 / 104 / 180` | Đạt |
| Món có cột `Cách dùng` khôi phục từ nguồn gốc | `1.096 / 3.732 (29.4%)` | Đạt |
| Món khớp dinh dưỡng thật từ bảng Viện Dinh dưỡng (NIN) | `2.784 / 3.732 (74.6%)` | Đạt |

## 2. Xử lý các lỗi phát hiện ở bộ gốc ViFoodRec
- Đã loại bỏ `ratings.csv` (182.678 dòng random đều 0–5) và 5 cột dinh dưỡng random (`calories`, `fat`, `fiber`, `sugar`, `protein`).
- Đã sửa triệt để lỗi hỏng chữ `muỗngl` → `ml`, `muỗngiếng` → `miếng` và 99 dòng lỗi `non-NFC`.
- Đã phân loại lại thành 13 nhóm món tiếng Việt rõ ràng thay cho nhãn gốc bị lệch 95% là `Món mặn`.
