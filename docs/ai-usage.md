# Khai báo dùng AI

README của nhóm có mục "Dùng AI vào việc gì" (2–3 dòng, bắt buộc). Ghi chi tiết vào bảng dưới đây.

> Luật của đề: dùng AI để làm bài thoải mái, nhưng **ai không giải thích được phần có tên mình thì phần đó nhận 0 điểm**. Khai thiếu không bị trừ; giấu mới bị.

| Việc | Công cụ AI | AI làm gì | Người kiểm/sửa gì | Ai phụ trách |
|---|---|---|---|---|
| Code bản chạy thử | Codex, Antigravity | Dựng khung UI web, workflow 8 bước, SQLite storage (`workflow.py`, `storage.py`, `web_preview.py`), adapter OpenRouter/Gemini (`ai.py`) | Đinh Lê Thịnh kiểm logic ràng buộc & luồng chính; Nguyễn Xuân Dương kiểm giao diện; Trần Duy Mạnh kiểm adapter Gemini & `simulate` | Đinh Lê Thịnh, Nguyễn Xuân Dương, Trần Duy Mạnh (`ai.py`) |
| Prompt / thiết kế lời gọi mô hình | Codex | Soạn và tinh chỉnh system prompt trích xuất & gợi ý món trong `workflow.py` | Kiểm chéo quy tắc G10, điều kiện dị ứng và JSON schema | Đinh Lê Thịnh |
| Đào data (viết script đếm, gợi ý nhãn) | Antigravity | Viết `scripts/build_vietnamese_dishes_csv.py` và script kiểm toán dữ liệu | Kiểm lọc 107 món ngoại, 158 trùng lặp, 3 thiếu thành phần; đối chiếu 2.784/3.732 món khớp NIN | Trần Duy Mạnh |
| Rà câu hỏi phỏng vấn / khảo sát | Antigravity | Chỉ rà câu dẫn dắt và cấu trúc câu hỏi đóng (`evidence/survey/questions.md`) | Thu 127 phiếu thật, lọc 56 phiếu hợp lệ (`evidence/survey/results_valid.csv`) | Trần Thị Hồng Gấm |
| Viết câu thử (benchmark) | Antigravity, Codex | Đề xuất cấu trúc B01–B15 và mở rộng ca kiểm thử B16–B27 | Đối chiếu giá/mã món với `restaurants_sample.json` v4; gắn nguồn `data_that` (9/27) và `tu_viet` (18/27) | Đinh Lê Thịnh, Trần Duy Mạnh |
| Sinh data `synthetic` (nếu có) | Không dùng | Không sinh người dùng/khảo sát giả (`restaurants_sample.json` là menu mẫu thiết kế có kiểm soát) | Đối chiếu 52 mã `VN-…` từ `vietnamese_dishes.csv` | Trần Duy Mạnh, Đinh Lê Thịnh |
| Chấm cột `pass` bằng LLM (nếu có) | Codex | Chấm sơ bộ 27 câu trong `eval/run-1.csv` theo `pass_criterion` | **Trần Duy Mạnh** (người chấm độc lập ngoài phần `workflow.py`/prompt) chấm đối chiếu lại `eval/run-1.csv`, xác nhận kết quả `20/27` | Trần Duy Mạnh |
| Rà soát lỗi, vá code P0 và chấm sơ bộ `run-6` | Claude Code | Rà toàn repo, viết 53 câu kiểm diễn đạt khác bộ câu thử, vá `workflow.py`/`tools.py` kèm test `tests/test_fix_*.py`, chấm sơ bộ `eval/run-6.csv` | Người trong nhóm đối chiếu cột `pass` của `eval/run-6.csv` | Trần Duy Mạnh |
| Slide, văn bản | Antigravity | Rà soát `spec.md`, `canvas.md`, `README.md`, `docs/PIPELINE.md` | Kiểm chứng số liệu thật và đối chiếu chuẩn rubric | Trần Thị Hồng Gấm, Trần Duy Mạnh |

**Không dùng AI để:** tạo người được phỏng vấn, trích dẫn, câu trả lời khảo sát; sửa kết quả các lượt đã chạy (`eval/run-*.csv`, `cost/simulate-*.csv`, `traces/`).
