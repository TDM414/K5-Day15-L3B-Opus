# Khai báo dùng AI

README của nhóm có mục "Dùng AI vào việc gì" (2–3 dòng, bắt buộc). Ghi chi tiết vào bảng dưới đây.

> Luật của đề: dùng AI để làm bài thoải mái, nhưng **ai không giải thích được phần có tên mình thì phần đó nhận 0 điểm**. Khai thiếu không bị trừ; giấu mới bị.

| Việc | Công cụ AI | AI làm gì | Người kiểm/sửa gì | Ai phụ trách |
|---|---|---|---|---|
| Code bản chạy thử | Antigravity, Codex | Dựng khung UI web, workflow 8 bước, SQLite storage, adapter OpenRouter và kiểm thử công cụ | Kiểm toàn bộ logic ràng buộc, sửa prompt và kiểm tra chạy `python run.py` | Trần Duy Mạnh, Đinh Lê Thịnh, Nguyễn Xuân Dương |
| Prompt / thiết kế lời gọi mô hình | Codex, Antigravity | Soạn và tinh chỉnh system prompt trích xuất và gợi ý món | Kiểm chéo quy tắc G10, điều kiện dị ứng và JSON schema | Trần Duy Mạnh |
| Đào data (viết script đếm, gợi ý nhãn) | Antigravity | Viết `scripts/build_vietnamese_dishes_csv.py` và script kiểm toán dữ liệu | Kiểm lọc 107 món ngoại, 158 trùng lặp, 3 thiếu thành phần; đối chiếu 2.784/3.732 món khớp NIN | Trần Duy Mạnh |
| Rà câu hỏi phỏng vấn / khảo sát | Antigravity | Chỉ rà câu dẫn dắt và cấu trúc câu hỏi đóng (`evidence/survey/questions.md`) | Thu 127 phiếu thật, lọc 56 phiếu hợp lệ (`evidence/survey/results_valid.csv`) | Trần Thị Hồng Gấm |
| Viết câu thử (benchmark) | Antigravity, Codex | Đề xuất cấu trúc B01–B15 và mở rộng ca kiểm thử B16–B27 | Đối chiếu giá/mã món với `restaurants_sample.json` v4; gắn nguồn `data_that` (9/27) và `tu_viet` (18/27) | Đinh Lê Thịnh, Trần Duy Mạnh |
| Sinh data `synthetic` (nếu có) | Không dùng | Không sinh người dùng/khảo sát giả (`restaurants_sample.json` là menu mẫu thiết kế có kiểm soát) | Đối chiếu 52 mã `VN-…` từ `vietnamese_dishes.csv` | Trần Duy Mạnh |
| Chấm cột `pass` bằng LLM (nếu có) | Codex | Chấm sơ bộ cột `pass` và `ghi_chu` của 27 câu trong `eval/run-1.csv` theo `pass_criterion` | Trần Duy Mạnh kiểm tra lại kết quả chấm (tổng 20/27 đạt) | Trần Duy Mạnh |
| Slide, văn bản | Antigravity | Rà soát `spec.md`, `canvas.md`, `README.md`, `docs/PIPELINE.md` | Kiểm chứng số liệu thật và đối chiếu chuẩn rubric | Trần Thị Hồng Gấm, Trần Duy Mạnh |

**Không dùng AI để:** tạo người được phỏng vấn, trích dẫn, câu trả lời khảo sát; sửa kết quả các lượt đã chạy (`eval/run-*.csv`, `cost/simulate-*.csv`, `traces/`).
