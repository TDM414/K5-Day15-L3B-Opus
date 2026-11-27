# Tổng hợp bằng chứng pain

> Điền ở guide bước 1.2, xong trước **CP3 10:00 Thứ Bảy 28/11**. Chấm ở rubric R1.
> Ba nguồn ngang nhau — tối thiểu **≥1 nguồn đạt ngưỡng**. Mạnh nhất: đào data ra insight → hỏi người dùng để kiểm lại (hoặc ngược lại).

## 1. Nguồn đã dùng

| Nguồn | Đạt ngưỡng? | File |
|---|---|---|
| Đào data (x/N, %, cách đếm chạy lại được, ≥5 ví dụ) | ☐ | Chưa dùng |
| Phỏng vấn (≥3 người ngoài nhóm, đúng người dùng) | ☐ | Chưa có ghi chép phỏng vấn trong repo |
| Khảo sát (≥20 người ngoài nhóm, đúng người dùng) | ☑ | 56 phiếu hợp lệ. [Câu hỏi khảo sát](survey/questions.md) · [Phiếu hợp lệ](survey/results_valid.csv) |

## 2. Số chính

- Số dưới đây tính từ **56 phiếu khảo sát hợp lệ** trong `survey/results_valid.csv`. Các phiếu đều trả lời “Có” ở Câu 1 về việc đặt cơm trưa hộ nhóm từ 3 người trong tháng qua. Theo ghi chép khảo sát, biểu mẫu thu **127 phiếu** từ 14:32 đến 16:15 ngày 27/11/2026.
  - **Tần suất & quy mô nhóm:** `33/56 (58.9%)` đặt 1–2 lần/tháng, `18/56 (32.1%)` đặt 3–5 lần/tháng, `5/56 (8.9%)` đặt ≥ 6 lần/tháng; `41/56 (73.2%)` nhóm 3–4 người, `15/56 (26.8%)` nhóm ≥ 5 người.
  - **Cách gom món & chia ship:** `21/56 (37.5%)` dùng link đơn nhóm (Grab/ShopeeFood), `17/56 (30.4%)` hỏi miệng, `13/56 (23.2%)` nhắn nhóm chat, `5/56 (8.9%)` đặt món quen; **`38/56 (67.9%)`** chia đều phí ship vào ngân sách từng người (`8/56 = 14.3%` chia theo giá món).
  - **Thời gian & số lượt sửa giỏ:** `44/56 (78.6%)` tốn ≥ 5 phút mỗi lần chốt đơn (`27/56 = 48.2%` mất 5–15p; `15/56 = 26.8%` mất 15–30p; `2/56 = 3.6%` >30p); **`29/56 (51.8%)`** phải hỏi lại hoặc sửa giỏ ≥ 1 lần (`24/56` sửa 1–2 lần, `5/56` sửa ≥ 3 lần).
  - **Vướng mắc cụ thể (chọn nhiều):** **`37/56 (66.1%)`** gặp ≥ 1 trong 3 vướng mắc lõi của D2: có người nói *"ăn gì cũng được"* (`32/56 = 57.1%`), có người kiêng/dị ứng (`16/56 = 28.6%`), vượt mức chi khi cộng phí ship (`14/56 = 25.0%`); ngoài ra quán hết món phải đổi là `25/56 (44.6%)`.
  - **Xử lý "ăn gì cũng được":** `29/56 (51.8%)` chọn hộ và họ ăn bình thường; `18/56 (32.1%)` yêu cầu tự chọn; `4/56 (7.1%)` chọn hộ nhưng bị đổi ý/không ưng.
  - **Mức phiền toái (1–5):** trung bình **2.48/5**; `26/56 (46.4%)` chấm từ 3 trở lên (`11/56 = 19.6%` chấm mức 4–5).

## 3. Năm ví dụ nguyên văn từ phiếu khảo sát

Các ví dụ là câu trả lời được chọn trong biểu mẫu câu hỏi đóng. Mỗi dòng trích đúng nội dung một ô từ một phiếu ẩn danh trong [results_valid.csv](survey/results_valid.csv). Số dòng tính cả tiêu đề CSV ở dòng 1.

| Tình huống | Nguồn trong CSV | Câu trả lời nguyên văn |
|---|---|---|
| Thành viên nói món gì cũng được | Dòng 12, Câu 7 | Có người nói "ăn gì cũng được" |
| Có điều kiện ăn uống cần kiểm tra | Dòng 23, Câu 7 | Có người kiêng / dị ứng món |
| Vượt ngân sách sau khi cộng ship | Dòng 26, Câu 7 | Vượt mức chi khi cộng phí ship |
| Phải đổi do món hết hàng | Dòng 13, Câu 7 | Quán hết món phải đổi |
| Phải hỏi lại hoặc sửa giỏ nhiều lần | Dòng 19, Câu 6 | Trên 5 lần |

## 4. Các nguồn có khớp nhau không

Khảo sát là nguồn bằng chứng hiện có. Trong 56 phiếu, 37 phiếu ghi nhận ít nhất một trong ba vướng mắc lõi của D2 và 29 phiếu cho biết phải hỏi lại hoặc sửa giỏ. Mức phiền trung bình là 2,48/5 và 16/56 phiếu chọn mức 1. Biểu mẫu đóng ghi nhận hành vi và mức phiền, còn nguyên nhân khiến từng nhóm gặp khó chưa được kiểm chứng bằng nguồn thứ hai.

## 5. Kết luận

Kết quả khảo sát ủng hộ phần lõi của [giả thuyết](hypothesis.md). 37/56 phiếu ghi nhận ít nhất một vướng mắc lõi và 29/56 phiếu ghi nhận việc hỏi lại hoặc sửa giỏ. Chưa có dữ liệu về mức tiết kiệm thời gian sau khi dùng Lunchie hoặc mức chấp nhận món do AI gợi ý.
