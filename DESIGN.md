# Hệ thiết kế Lunchie

Tài liệu định hướng cho giao diện web CP3. Đối tượng, hành trình và giới hạn sản phẩm nằm trong [PRODUCT.md](PRODUCT.md).

## Hướng thị giác

Cam ấm, gọn gàng và sang trọng theo tinh thần văn phòng. Lấy **cam từ áo đầu bếp**, **kem từ mũ và bát**, **nâu đậm từ đường viền** làm ba màu nhận diện. Giữ phần lớn diện tích sáng để đọc nhanh. Tạo độ tinh tế bằng lề thẳng hàng, khoảng trắng đều và đường phân cách mảnh. Dùng cam đậm có chủ đích ở hành động chính và quán đã chọn. Làm nổi tổng tiền bằng chữ đậm và số căn thẳng cột.

## Mascot đồng hành

Dùng ảnh **Chibi Chef Girl with Ramen Bowl.png** do chủ dự án cung cấp. Giữ tỷ lệ, màu gốc và nền trong suốt. Navbar của trang giới thiệu và ứng dụng đặt mascot 40 px ngay bên trái chữ **Lunchie**, trong cùng một liên kết về trang giới thiệu. Trang giới thiệu đặt mascot cạnh giỏ ví dụ. Trong mỗi bước của ứng dụng, đặt mascot ngay sau tiêu đề bước, gần thao tác đầu tiên.

- Dùng cùng một hàng hướng dẫn gồm ảnh mascot và một câu ngắn từ [PRODUCT.md](PRODUCT.md#mascot-hướng-dẫn). Ảnh cao khoảng 64 px trên desktop và 44 px trên mobile. Cho chữ xuống dòng tự nhiên.
- Giữ mascot ở đúng một vị trí trong luồng đọc. Tránh hộp thoại che form hoặc hiệu ứng lặp. Dùng `alt=""` cho ảnh vì lời hướng dẫn đã có dạng văn bản.
- Nếu người dùng ẩn lời hướng dẫn, giữ lựa chọn cho các bước tiếp theo trong phiên. Nhãn nút và hướng dẫn bắt buộc của biểu mẫu vẫn cung cấp đủ thông tin để hoàn thành tác vụ.

## Màu và vai trò

Khai báo các giá trị dưới đây một lần dưới dạng CSS variables. Dùng tên theo vai trò trong component.

| Token | Giá trị | Vai trò |
| --- | --- | --- |
| `--color-bg` | `#FFF8F2` | Nền trang |
| `--color-surface` | `#FFFEFC` | Form, thẻ quán và khối giỏ |
| `--color-text` | `#2C1B14` | Chữ chính và tiền |
| `--color-text-muted` | `#6C5143` | Chữ phụ và hướng dẫn |
| `--color-divider` | `#EFDED3` | Đường phân nhóm trang trí |
| `--color-control-border` | `#A37C67` | Viền ô nhập và nút phụ |
| `--color-accent` | `#FF7900` | Điểm nhấn nhận diện |
| `--color-primary` | `#B84208` | Nút chính, link và vòng focus trên nền sáng |
| `--color-primary-hover` | `#9A3506` | Nút chính khi hover hoặc active |
| `--color-on-primary` | `#FFFFFF` | Chữ nút chính |
| `--color-selected-bg` / `--color-selected-text` | `#FFEBDA` / `#71330F` | Quán đang chọn hoặc bước hiện tại |
| `--color-danger-bg` / `--color-danger-text` | `#FFF0ED` / `#A82921` | Lỗi cần người dùng sửa |
| `--color-warning-bg` / `--color-warning-text` | `#FFF1CD` / `#694600` | Cần bổ sung hoặc chú ý |
| `--color-success-bg` / `--color-success-text` | `#EAF6ED` / `#23603C` | Giỏ đã qua kiểm tra |

Chữ trắng trên nút cam đậm đạt khoảng **5,50:1**. Nếu có chữ trên cam sáng, dùng chữ nâu đậm. Mỗi trạng thái có nhãn chữ dễ hiểu. Dùng vòng focus 2 px, cách viền 2 px, và kiểm lại độ tương phản khi ghép màu mới.

## Chữ, khoảng cách và hình khối

- Dùng **Be Vietnam Pro**, dự phòng `system-ui, sans-serif`. Cỡ chữ 30 px cho tiêu đề desktop, 24 px trên mobile, 20 px cho đầu mục, 16 px cho nội dung và ô nhập, 14 px cho phụ chú. Trọng lượng 400 cho nội dung, 600 cho nhãn và nút, 700 cho tiêu đề và tổng tiền.
- Dùng chữ số cùng độ rộng khi font hỗ trợ (`font-variant-numeric: tabular-nums`). Căn phải cột tiền trên desktop. Ghi `48.000đ` và giữ số tiền trên một dòng.
- Thang khoảng cách 4, 8, 12, 16, 24, 32, 48 px. Bo góc 8 px cho điều khiển, 12 px cho khối chính. Ưu tiên nền phẳng và đường phân cách. Dùng khoảng trắng để nhóm các phần liên quan.

## Bố cục chung

- Khung nội dung rộng tối đa 1120 px. Trên desktop từ 960 px, dùng cột thao tác linh hoạt và một cột tóm tắt khoảng 300 px khi đã có dữ liệu để tóm tắt. Chừa 24 px giữa hai cột.
- Trên mobile, dùng một cột, lề ngang 16 px và thanh tiến trình gọn theo bước hiện tại. Nếu đặt nút chính cố định dưới màn hình, chừa khoảng đệm để nút và bàn phím không che trường đang sửa.
- Xếp theo thứ tự tiêu đề bước, nội dung thao tác, trạng thái và hành động chính. Dùng một nút chính trong mỗi khu vực ra quyết định. “Quay lại”, “Tải ví dụ” và “Sao chép tin nhắn nháp” dùng kiểu phụ.

## Mẫu component cần tái sử dụng

| Component | Quy tắc |
| --- | --- |
| **Thanh tiến trình** | Dùng bốn tên bước từ PRODUCT. Phân biệt bước hiện tại bằng chữ và `aria-current="step"`. |
| **Hướng dẫn của mascot** | Một hàng gọn ở đầu nội dung, dùng chung bố cục và đổi lời nhắc theo bước. |
| **Ô nhập có lỗi** | Giữ nhãn hiển thị, đặt lỗi cạnh trường. Liên kết lỗi bằng `aria-describedby` và đánh dấu `aria-invalid` khi cần. |
| **Dòng thành viên** | Tên là điểm bắt đầu. Nhóm điều kiêng, món muốn ăn và ngân sách theo người. Trên mobile cho xuống dòng theo từng nhóm. |
| **Thẻ quán** | Hiện tên, phí ship/người và căn cứ phù hợp với nhóm. Thẻ đang chọn có viền, nền và chữ **Đã chọn**. |
| **Dòng giỏ** | Ưu tiên tên món, nhãn **Túi mù** khi có, `giá món + ship = tổng` và nút **Đổi món** cạnh người tương ứng. Dòng có lỗi hiển thị lý do tại chỗ. |
| **Phản hồi thao tác** | Trong lúc xử lý, dùng chữ như “Đang đọc yêu cầu…”. Lỗi model có **Thử lại** và giữ nội dung. Trạng thái động cần được thông báo cho công nghệ hỗ trợ. |

Lấy **Chốt giỏ** làm màn hình chuẩn khi rà style. Mượn từ màn này cách xử lý số tiền, dòng thành viên, nút và lỗi cho các bước còn lại. Dành màu cam cho hành động và điểm cần chú ý. Bỏ các khối chỉ lặp nội dung, badge trên tiêu đề và card lồng card.

## Rà trước khi giao

- Mở ở 390 px và 1440 px. Kiểm tra tên người và tên món dài, nhóm từ 5 người, giá VNĐ và nút đổi món có đủ chỗ.
- Duyệt bằng bàn phím. Focus luôn nhìn thấy. Nút và trường chính trên mobile cao tối thiểu 44 px. Nút cố định không che nội dung ở cuối.
- Thử các trạng thái thiếu ngân sách, đang chờ, lỗi kết nối, không có giỏ, giỏ đã kiểm, đổi lần hai và chốt thành công. Đối chiếu nhãn trạng thái với kết quả thực tế của ứng dụng.
- Kiểm tra lời mascot ở cả bốn bước. Lời nhắc phải chỉ đúng việc tiếp theo, kể cả khi đọc ở màn hình hẹp. Kiểm tra lại thao tác khi người dùng đã ẩn hướng dẫn.
- Trước khi thêm màu, kiểu nút hoặc kiểu nhãn mới, kiểm tra mẫu tương ứng trong tài liệu và code đang dùng.
