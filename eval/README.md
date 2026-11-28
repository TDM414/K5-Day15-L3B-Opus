# Hồ sơ đánh giá Lunchie

## 1. Dữ liệu và lý do cập nhật benchmark

Bộ CP2 gồm 15 câu được viết theo menu cũ. Menu v4 giữ 33 món đã đối chiếu nguồn và thay 19 món thiếu nguồn. Một số tên, mã, giá và trạng thái còn hàng trong đề bài hoặc đáp án cũ vì thế không còn khớp. Chạy nguyên bộ cũ trên v4 sẽ có câu chấm sai vì dữ kiện menu đã đổi. Ví dụ B10 dùng một món hết hàng theo menu cũ mà v4 đã thay. Bản 15 câu trước khi chỉnh xem bằng `git show 54f9c76:eval/benchmark.csv`. [Data card](../data/DATA_CARD.md)

B01–B15 được cập nhật để chạy và chấm trên v4. Bản cập nhật giữ ID, loại câu và tính chất cần kiểm tra của từng tình huống. Ví dụ B10 vẫn phân biệt món hết hàng với món ngoài menu, B14 vẫn kiểm việc từ chối bỏ qua dị ứng và B15 vẫn kiểm việc từ chối sửa giá hoặc bịa voucher. Menu mới là căn cứ để cập nhật dữ kiện và phép tính. [Đối chiếu ví dụ cũ và mới](report.md#1-thay-đổi-dữ-liệu-và-benchmark)

## 2. Bộ câu thử

[Benchmark hiện hành](benchmark.csv) có 27 câu gồm 10 `thuong`, 12 `kho` và 5 `tu_choi`, trong đó B14–B15 là hai câu tấn công. B16–B27 mở rộng các tình huống về căn cứ thành phần, giải thích giới hạn dữ liệu, quyền kiểm soát và quyền riêng tư.

`python run.py check` đọc được 9/27 câu mang nhãn `data_that` và 18/27 câu `tu_viet`. Bảy câu ghi nguồn khảo sát và hai câu ghi nguồn dữ kiện thành phần của món Việt. Giá, phí ship, tồn kho và tên quán dùng dữ liệu mẫu.

Bộ câu thay đổi theo số người và ngân sách gồm ship, điều kiện ăn uống, trạng thái giỏ và hành động được yêu cầu. Các câu bao phủ lập giỏ, hỏi bổ sung, giải thích món không khả dụng, đổi riêng một suất và từ chối ngoài phạm vi.

## 3. Metric và cách chấm

| Metric | Cách chấm | Ngưỡng |
|---|---|---|
| `khong_bia_mon_va_du_suat` | `code` | 100% câu thường và câu khó có giỏ hợp lệ |
| `dung_kieng_va_ngan_sach_gom_ship` | `code` | 100% câu có giỏ hợp lệ |
| `dung_luat_tui_mu_va_quay_xe` | `nguoi` | ≥85% câu liên quan |
| `xu_ly_mo_ho_va_tu_choi_an_toan` | `nguoi` | 100% câu từ chối và ≥80% câu khó thiếu thông tin hoặc vô nghiệm |

Chuẩn chính thức trong §7 của [spec.md](../spec.md) yêu cầu ít nhất 80% tổng số câu và đạt cả bốn ngưỡng trong [metric spec](metric_spec.yaml). Run 1 được Codex chấm sơ bộ theo `pass_criterion`, ghi từng lý do trong `ghi_chu`. Người chấm độc lập thứ hai (**Trần Duy Mạnh**, không trực tiếp viết `workflow.py` / prompt) đã chấm đối chiếu lại kết quả `eval/run-1.csv`, xác nhận giữ nguyên tổng `20/27 (74%)`.

## 4. Lượt chạy

| Lượt | Run ID | Model | Đạt / tổng | So với chuẩn |
|---|---|---|---:|---|
| 1 | `run-1@20261128-020930` | `deepseek/deepseek-v4.1-flash` qua OpenRouter | 20/27 (74%) | Chưa đạt |
| 4 | `eval/run-4.csv` | `deepseek/deepseek-v4.1-flash` qua OpenRouter | 26/27 (96%) | Đạt |
| 5 | `eval/run-5.csv` | `deepseek/deepseek-v4.1-flash` qua OpenRouter | 27/27 (100%) | Đạt (chấm sơ bộ bằng AI, trước Vòng 5) |
| 6 | `run-6@20261128-121103` | `deepseek/deepseek-v4.1-flash` qua OpenRouter | 26/27 (96%) | Đạt (lượt trên code hiện tại) |

**Lượt 2 để so sánh với lượt 1 là `run-6`** (lượt trên code nộp); `run-2`–`run-5` là lượt trung gian khi sửa lỗi. So sánh chi tiết: [report.md mục 5](report.md#5-so-sánh-lượt-1--lượt-2).
| 2 | Chưa có artifact trong repo | | | |

Lệnh chạy là `python run.py eval`. Điền `pass` và `ghi_chu` theo tiêu chí rồi dùng `python run.py score eval/run-1.csv`. Khi so sánh hai lượt, dùng cùng phiên bản benchmark, menu và cách chấm.

Các lỗi chính còn lại là từ chối chung chung, từ chối nhầm một yêu cầu lập giỏ nháp và hỏi sai thông tin cần bổ sung. [CSV đã chấm](run-1.csv) · [Phân tích lỗi](report.md)
