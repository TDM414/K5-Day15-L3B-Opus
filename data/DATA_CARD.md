# Data card — dữ liệu bản chạy thử dùng

> Cập nhật cho **CP2** (Pipeline 8 bước D2). Toàn bộ dữ liệu gốc được giữ bất biến trong `data/raw/` và `data/sources/` (không commit file thô lớn); dữ liệu bản chạy thử sử dụng nằm trong `data/`.

## Dataset 1 · `data/restaurants_sample.json` (Danh sách quán & menu cơm trưa văn phòng D2)

|  |  |
| --- | --- |
| Dùng để làm gì | Nguồn dữ liệu chính cho công cụ gợi ý tối đa 3 quán, đọc menu, dựng giỏ (kèm túi mù) và code kiểm tra ràng buộc món/tồn hàng/dị ứng/ngân sách gồm ship (`codebase/tools.py`). |
| Từ đâu | Tên món Việt và thuộc tính ẩm thực tham chiếu từ bộ món ăn Việt đã lọc sạch (`data/processed/vietnamese_dishes.csv`); tên 4 quán mẫu, giá bán VNĐ, phí giao hàng và trạng thái còn hàng (`in_stock`) do nhóm thiết kế có kiểm soát cho bài toán D2. |
| Xử lý những bước gì | Chọn 4 quán đại diện (`Q01` Bếp Cơm Nhà Văn Phòng, `Q02` Cơm Ngon Ba Miền, `Q03` Bún Phở & Cơm Đĩa Phố Cổ, `Q04` Bếp Chay & Eat Clean Xanh); chuẩn hóa schema JSON gồm `restaurant_id`, `shipping_fee_vnd`, `dish_id`, `ten_mon`, `price_vnd`, `che_do_an`, `huong_vi`, `allergens`, `is_vegetarian`, `in_stock`; cài 2 món hết hàng (`in_stock: false`) để kiểm thử kịch bản thực tế. |
| Số dòng / số cột | **4 quán** · **28 món ăn** (mỗi món có 9 trường chuẩn hóa). |
| Phiên bản / ngày lấy | 2026-11-27 |
| Nhãn | **hỗn hợp (tên món & thuộc tính tham chiếu thật + giá/quán mẫu có kiểm soát cho D2)** — ghi rõ để không nhầm với giá real-time trên app thương mại. |
| Giới hạn | Không phản ánh biến động giá và tồn kho trực tiếp từ GrabFood/ShopeeFood; số lượng quán mẫu cố định 4 quán (gợi ý tối đa 3 quán/lượt); không chứa thông tin khuyến mãi/voucher app. |

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