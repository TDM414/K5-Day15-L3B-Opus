# Data card — dữ liệu bản chạy thử dùng

> Menu mẫu hiện dùng phiên bản **4**. Dữ liệu công thức nằm riêng trong `data/processed/vietnamese_dishes.csv`.

## Dataset 1 · `data/restaurants_sample.json` (Danh sách quán & menu cơm trưa văn phòng D2)

|  |  |
| --- | --- |
| Dùng để làm gì | Nguồn dữ liệu chính cho công cụ gợi ý tối đa 3 quán, đọc menu, dựng giỏ (kèm túi mù) và code kiểm tra ràng buộc món/tồn hàng/dị ứng/ngân sách gồm ship (`codebase/tools.py`). |
| Từ đâu | 52 món có mã `VN-…` từ `data/processed/vietnamese_dishes.csv`. Tên quán, giá bán VNĐ, phí giao hàng và trạng thái tồn kho do nhóm mô phỏng. |
| Xử lý những bước gì | Giữ 33 món đã đối chiếu nguồn, thay 19 món thiếu nguồn bằng suất ăn khác có công thức và cấp mã món mới. `metadata.serving_size: 1` áp dụng cho mọi món. Khẩu phần gốc tra trong CSV qua `source_dish_id`. |
| Số dòng | **6 quán · 52 món · 2 món hết hàng**. |
| Phiên bản / ngày lấy | 2026-11-27 |
| Nhãn | **hỗn hợp (tên món & thuộc tính tham chiếu thật + giá/quán mẫu có kiểm soát cho D2)** — ghi rõ để không nhầm với giá real-time trên app thương mại. |
| Giới hạn | Gợi ý tối đa 3 quán/lượt. Giá và tồn kho chỉ dùng trong demo. Công thức tham chiếu có thể thiếu thông tin về gia vị pha sẵn hoặc chế biến chung. |

- `source_dish_id` nối mọi món với công thức tương ứng hoặc công thức phần món chính. `ingredients` giữ nguyên văn toàn bộ cột `thanh_phan`. Chín món CP2 đã nối vẫn có trạng thái `legacy_partial` vì công thức tham chiếu chưa mô tả đầy đủ suất của quán mẫu.
- `allergens` giữ nhãn dị ứng nhận diện được. `ingredient_tags` chứa nguồn đạm hoặc nguyên liệu dùng để kiểm điều kiêng. `is_vegetarian` là cờ ăn chay. Các số trung bình trên 100 g nguyên liệu trong CSV không được dùng làm số dinh dưỡng cho một suất.
- `is_spicy` là `true` hoặc `false` khi có đủ căn cứ trong dữ liệu, và `null` khi nguồn chưa rõ. Món có `csv_partial` chứa thành phần tham chiếu còn thiếu chi tiết. `csv_listed` biểu thị danh sách nguyên liệu đơn giản được ghi rõ trong nguồn để đối chiếu trong demo. Với yêu cầu dị ứng rõ ràng, hệ thống yêu cầu xác nhận thành phần cho món thiếu chi tiết. Thành phần tham chiếu và mảng `allergens` rỗng không xác nhận an toàn khi đặt thật.
- Bộ kiểm sử dụng nguyên liệu CSV của các món bổ sung. Khi kiểm món CP2, bộ kiểm dựa vào thông tin đã khai báo trong menu mẫu. Ngữ cảnh chọn món của model chỉ nhận các trường phục vụ lựa chọn và kiểm ràng buộc.

## Dataset 2 · `data/processed/vietnamese_dishes.csv` (Kho món ăn Việt Nam đã kiểm toán — dữ liệu nền tham chiếu)

|  |  |
| --- | --- |
| Dùng để làm gì | Kho tham chiếu mở rộng tên món, thành phần, phân loại 13 nhóm món và dinh dưỡng thật theo Viện Dinh dưỡng Quốc gia (`outputs/sanity_check/data_health_report.md`). |
| Từ đâu | Bộ ViFoodRec (làm sạch & ghép `Cách dùng`/`Mách nhỏ`) đối chiếu dinh dưỡng thật từ bảng Viện Dinh dưỡng Quốc gia (`MIT`, `scripts/build_vietnamese_dishes_csv.py`). |
| Xử lý những bước gì | Loại bỏ `ratings.csv` và 5 cột dinh dưỡng sinh ngẫu nhiên từ bộ gốc; lọc bỏ 107 món ngoại + 158 trùng lặp + 3 thiếu thành phần; sửa lỗi chữ & chuẩn hóa 100% Unicode `NFC`; phân loại lại thành 13 nhóm món tiếng Việt; đối chiếu dinh dưỡng NIN (`2.784/3.732` món khớp). |
| Số dòng / số cột | **3.732 món ăn** × **23 cột** (`dish_id`, `ten_mon`, `thanh_phan`, `loai_mon`, `nhiet_do_phuc_vu`, `vung_mien`, `huong_vi`, `che_do_an`, `khau_phan`, `thoi_gian_nau_phut`, `cach_dung`, `mach_nho`, `mo_ta_ngan`, `tags`, các cột dinh dưỡng NIN, `nguon_du_lieu`, `ngay_xu_ly`). |
| Phiên bản / ngày lấy | 2026-11-27 |
| Nhãn | **thật** |
| Giới hạn | Không có giá bán VNĐ và không nhóm sẵn theo từng quán ăn cụ thể; do đó nhóm không dùng trực tiếp để tính tiền mà trích cấu trúc món sang `data/restaurants_sample.json`. |
