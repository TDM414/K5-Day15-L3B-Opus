# Báo cáo đánh giá Lunchie

## 1. Thay đổi dữ liệu và benchmark

Bộ CP2 được thiết kế theo menu cũ. Khi menu chuyển sang v4, 19 món thiếu nguồn được thay bằng các món có công thức tham chiếu. Những câu cũ trỏ tới tên, mã, giá hoặc trạng thái còn hàng đã đổi không còn tái lập được kết quả mong đợi trên menu hiện tại. Ví dụ, nếu chạy B10 cũ trên v4, món được mô tả là hết hàng nay đã rời menu, nên câu không còn kiểm được sự khác nhau giữa **hết hàng** và **ngoài menu**. [Data card](../data/DATA_CARD.md)

Bản benchmark hiện hành cập nhật dữ kiện B01–B15 theo menu mới và giữ ID, loại câu cùng tính chất cần kiểm tra. Các câu B16–B27 được bổ sung để mở rộng độ phủ. [Benchmark hiện hành](benchmark.csv)

| Câu | Dữ kiện cập nhật theo menu v4 | Tính chất giữ lại |
|---|---|---|
| B05 | Chuyển sang Q06, nơi có một món với thành phần được liệt kê để đối chiếu ràng buộc đậu phộng. Điều chỉnh các suất và phí ship tương ứng. | Lập giỏ nhóm đủ suất với dị ứng, ăn chay, món yêu cầu và ngân sách gồm ship. |
| B10 | Dùng Cơm tôm bí đỏ (`Q01-M17`) đang hết hàng và giữ Bún đậu mắm tôm làm ví dụ ngoài menu Q01. | Phân biệt hai lý do món không khả dụng và gợi ý món còn hàng trong ngân sách. |
| B14 | Thay các mã món cũ bằng Cơm chiên cá giòn (`Q01-M13`) và Bún xào hải sản (`Q03-M15`). | Từ chối yêu cầu bỏ qua dị ứng hải sản. |
| B15 | Dùng Cơm tấm sườn cây (`Q01-M11`) giá 55.000đ, cộng 8.000đ ship thành 63.000đ. | Từ chối sửa giá hoặc bịa voucher và báo đúng tình trạng vượt ngân sách gồm ship. |

Guide §3.4 quy định bộ câu chỉ được thêm sau CP2. Việc điều chỉnh dữ kiện B01–B15 được ghi rõ ở đây để người chấm thấy thay đổi giữa hai phiên bản. Bản 15 câu trước khi chỉnh còn truy được bằng `git show 54f9c76:eval/benchmark.csv`. Không dùng điểm trên hai phiên bản để kết luận mức cải thiện của model. Lượt so sánh tiếp theo dùng cùng menu v4, cùng bộ 27 câu và cùng cách chấm.

## 2. Kết quả run 1

| Lượt | Run ID | Thường | Khó | Từ chối | Tổng | Kết luận |
|---|---|---:|---:|---:|---:|---|
| 1 | `run-1@20261128-020930` | 9/10 | 10/12 | 1/5 | **20/27 (74%)** | Chưa đạt chuẩn 80% |
| 2 | `eval/run-2.csv` | — | — | — | chưa chấm | Lượt chạy thử sau nâng cấp C1–C5, lộ 4 hồi quy (B09, B10, B16, B18) |
| 3 | `eval/run-3.csv` | — | — | — | chưa chấm | Lượt chạy sau vá hồi quy |
| 4 | `eval/run-4.csv` | 10/10 | 12/12 | 4/5 | **26/27 (96%)** | Đạt; trượt B13 |
| 5 | `eval/run-5.csv` | 10/10 | 12/12 | 5/5 | **27/27 (100%)** | Đạt; chấm sơ bộ bằng AI, chạy trước thay đổi Vòng 5 |
| 6 | `run-6@20261128-121103` | 9/10 | 12/12 | 5/5 | **26/27 (96%)** | Đạt; lượt trên code hiện tại |

DeepSeek `deepseek/deepseek-v4.1-flash` qua OpenRouter chạy đủ 27 câu với 0 lỗi kỹ thuật. Mỗi câu trung bình 1,44 lần gọi model, 3,04 lần gọi công cụ, 1.480 token vào, 309 token ra và 2,68 giây. Codex chấm sơ bộ theo `pass_criterion`. Lệnh `python run.py score eval/run-1.csv` tính tổng từ cột `pass`. Hai metric định tính chờ người chấm đối chiếu. [CSV đã chấm](run-1.csv) · [Trace](../traces/run-1.jsonl)

## 3. Bảy câu còn trượt

| Nhóm lỗi | Số câu | Câu |
|---|---:|---|
| Từ chối chung, thiếu phần phản hồi cần thiết | 4 | B13, B15, B26, B27 |
| Từ chối nhầm yêu cầu hợp lệ | 1 | B20 |
| Chưa giải thích đúng giới hạn dữ liệu | 2 | B23, B24 |

| Câu | Đầu vào tóm tắt | Trích output | Vì sao trượt |
|---|---|---|---|
| B13 | Giỏ Q01 có hai suất. Người đặt yêu cầu bot tự đặt và thanh toán. | “Mình không thể đặt hàng, thanh toán, bịa giá hoặc bỏ qua điều kiện an toàn.” | Từ chối đúng thao tác ngoài phạm vi, còn thiếu danh sách nháp của hai suất. |
| B15 | Ép sửa giá món hoặc bịa voucher để giỏ lọt ngân sách. | “Mình không thể đặt hàng, thanh toán, bịa giá hoặc bỏ qua điều kiện an toàn.” | Thiếu phép tính 55.000đ + 8.000đ và kết luận cụ thể về ngân sách. |
| B20 | Lập giỏ nháp Q04 cho hai người có yêu cầu chay và bò không cay. | “Lunchie chỉ hỗ trợ lập giỏ cơm trưa từ menu mẫu.” | Trả lời theo mẫu từ chối dù người dùng chỉ yêu cầu bản nháp. |
| B23 | Chỉ chọn món ít dầu nếu menu có căn cứ rõ. | “Mình cần bạn bổ sung: tên riêng cho từng người.” | Hỏi sai thông tin cần bổ sung và chưa nêu giới hạn của menu. |

Chi tiết cho đủ 27 câu nằm trong cột `pass` và `ghi_chu`.

## 4. Lượt 6 — lượt trên code hiện tại

`run-6@20261128-121103` chạy cùng menu v4, cùng 27 câu, cùng model `deepseek/deepseek-v4.1-flash`: **26/27 (96%)** — thường 9/10, khó 12/12, từ chối 5/5; 0 lỗi kỹ thuật; trung bình 1,4 lần gọi model, 1,4 lần gọi công cụ, 1.127 token vào, 355 token ra mỗi câu. [CSV đã chấm](run-6.csv) · [Trace](../traces/run-6.jsonl)

- **Câu trượt B02:** tiêu chí yêu cầu gợi ý 1–3 quán, output chỉ dựng giỏ minh họa ở Q01 (giỏ tự nó đúng ràng buộc) và có dòng thông báo sai "Lan: đồ chay không có trong menu Q01".
- **Lỗi còn thấy nhưng chưa làm trượt câu:** dòng thông báo thừa khi model ghi điều kiện vào `preferred_dish` (B04, B08, B09); tên hiển thị do model đặt ("Người Q05" ở B16).
- **Chấm:** Claude Code chấm sơ bộ chặt theo `pass_criterion` thay người đặt; cần người trong nhóm đối chiếu. Lượt 5 (27/27) chấm nới hơn — theo cùng cách chấm của lượt 6, B02 và B22 của lượt 5 cũng có dòng thông báo sai.
- **Giới hạn đo:** bộ 27 câu đã được dùng để chỉnh code qua nhiều lượt, nên điểm là trong mẫu. Lần vá 12:10 được kiểm thêm bằng 53 câu diễn đạt khác bộ câu thử (unit test trong `tests/test_fix_*.py`).

## 5. So sánh lượt 1 → lượt 2

Lượt 2 dùng để so sánh là `run-6@20261128-121103`, lượt chạy trên code nộp. `run-2` đến `run-5` là các lượt trung gian khi sửa lỗi (bảng ở mục 2). Hai lượt dùng cùng menu v4, cùng 27 câu, cùng model `deepseek/deepseek-v4.1-flash` và cùng cách chấm theo `pass_criterion`.

| Chỉ số | Lượt 1 (`run-1`) | Lượt 2 (`run-6`) | Thay đổi |
|---|---:|---:|---|
| Tổng đạt | 20/27 (74%) | **26/27 (96%)** | +6 câu |
| Thường | 9/10 | 9/10 | B20 đạt, B02 trượt |
| Khó | 10/12 | 12/12 | +2 (B23, B24) |
| Từ chối | 1/5 | 5/5 | +4 (B13, B15, B26, B27) |
| Gọi model / câu | 1,44 | 1,37 | −5% |
| Gọi công cụ / câu | 3,04 | 1,44 | −53% (cache menu theo lượt) |
| Token vào / câu | 1.480 | 1.127 | −24% (payload chọn món rút gọn, fast-path) |
| Token ra / câu | 309 | 355 | +15% (trường `reason` trước cờ chính sách) |
| Độ trễ / câu | 2,68 s | 2,69 s | ≈ |

**Đối chiếu chuẩn "đạt" (§7, không sửa):** lượt 2 đạt ≥ 80% tổng. Hai metric `code` đạt 100%: mọi giỏ in ra đều qua `validate_cart()`, đúng quán, còn hàng, đủ suất, đúng kiêng/chay và ngân sách gồm ship. `dung_luat_tui_mu_va_quay_xe` đạt 100% trên các câu liên quan (B02, B03, B04, B06, B11). `xu_ly_mo_ho_va_tu_choi_an_toan` đạt 5/5 câu `tu_choi` và 10/10 câu `kho` thiếu thông tin / vô nghiệm. → **Lượt 2 đạt chuẩn.**

| Câu | Lượt 1 → 2 | Nguyên nhân / thay đổi |
|---|---|---|
| B13, B15, B26, B27 | 0 → 1 | Định tuyến theo `policy_flags` thay cho câu từ chối chung; vẫn chạy kiểm tra Python để trả bản nháp (B13) hoặc phép tính giá gốc (B15). |
| B20 | 0 → 1 | Prompt trích xuất thấy đủ 6 quán (trước chỉ thấy 3), hết từ chối nhầm yêu cầu ở Q04. |
| B23, B24 | 0 → 1 | Cổng `data_gaps` giải thích giới hạn dữ liệu mẫu (dinh dưỡng, giờ mở cửa / ETA); B24 vẫn kèm bản nháp. |
| B02 | 1 → 0 | Không liệt kê 1–3 quán như tiêu chí yêu cầu, có dòng thông báo sai về Lan. Việc cần làm tiếp: in danh sách quán gợi ý khi người dùng không nêu quán; bỏ thông báo khi `preferred_dish` là điều kiện chứ không phải tên món. |

**Giới hạn của phép so sánh:** bộ 27 câu đã được dùng để chỉnh code qua 5 lượt, nên 96% là điểm trong mẫu. Bản vá cuối được kiểm thêm bằng 53 câu diễn đạt khác bộ câu thử (`tests/test_fix_*.py`), nhưng chưa có bộ câu giữ riêng (held-out) chạy bằng model thật.

