# Lunchie

Tên sản phẩm hiển thị ở đầu trang và trong tiêu đề trình duyệt.

## Platform

web

## Người dùng và tình huống

Ứng dụng giúp nhân viên văn phòng gom một đơn cơm trưa cho nhóm đồng nghiệp. Người đặt có thể bắt đầu bằng tin nhắn nhóm hoặc yêu cầu tự nhập. Họ cần đối chiếu điều kiêng, món muốn ăn và ngân sách đã gồm phí giao hàng trước khi chốt từng suất.

Trong khảo sát của nhóm, 29/56 người phải hỏi lại hoặc sửa giỏ ít nhất một lần, và 38/56 chia đều phí giao hàng vào ngân sách từng người. [Tổng hợp khảo sát](evidence/summary.md)

## Lời hứa của sản phẩm

**Gom yêu cầu, chọn một quán và chốt giỏ đã kiểm cho cả nhóm.** Người đặt thấy hệ thống hiểu gì, được sửa từng mục và biết mỗi người cần trả bao nhiêu. AI hỗ trợ trích yêu cầu và đề xuất món. Code kiểm giỏ theo menu mẫu và ràng buộc đã xác nhận. Người đặt duyệt và tự đặt trên ứng dụng giao đồ ăn.

## Trải nghiệm CP3

Website tiếng Việt, dùng được trên điện thoại và máy tính. Trang giới thiệu ở `/` minh họa một giỏ mẫu và dẫn vào ứng dụng ở `/app.html`. Bốn màn hình sau trình bày tám bước xử lý trong [Pipeline](docs/PIPELINE.md).

| Màn hình | Việc người đặt làm | Hành động chính |
| --- | --- | --- |
| **Nhập yêu cầu** | Dán tin nhắn, nhập ngân sách chung nếu có, hoặc tải một ví dụ mẫu để thử. | **Đọc yêu cầu** |
| **Xác nhận** | Kiểm tên, ngân sách, điều kiêng, món không thích và món muốn ăn của từng người. Sửa kết quả AI trích và bổ sung dữ kiện còn thiếu. | **Xác nhận và tìm quán** |
| **Chọn quán** | So sánh tối đa ba quán mẫu theo khả năng đáp ứng yêu cầu và phí giao hàng/người. Chọn một quán. | **Chọn quán này** |
| **Chốt giỏ** | Xem món và tổng tiền từng người, copy tin nhắn nháp, xử lý phản hồi đổi món và kiểm lại giỏ trước khi chốt. | **Chốt giỏ** |

## Mascot hướng dẫn

Đầu bếp chibi đồng hành ở cả bốn màn hình. Mỗi bước có một lời nhắc ngắn, chỉ đúng việc người đặt cần làm tiếp:

| Bước | Lời nhắc mẫu |
| --- | --- |
| **Nhập yêu cầu** | Dán tin nhắn nhóm để mình đọc món muốn ăn, điều kiêng và ngân sách. |
| **Xác nhận** | Kiểm lại điều kiêng và ngân sách từng người trước khi tìm quán. |
| **Chọn quán** | So sánh phí ship mỗi người rồi chọn một quán cho cả nhóm. |
| **Chốt giỏ** | Xem lại món và tổng tiền từng người, rồi chốt khi cả nhóm đã thống nhất. |

Lời nhắc thay đổi theo bước và có thể ẩn theo lựa chọn của người đặt. Lỗi nhập liệu và kết quả kiểm giỏ hiển thị riêng tại nơi cần xem hoặc sửa.

## Các quyết định cần thể hiện trên UI

- Giữ bản nháp khi quay lại bước trước hoặc khi lỗi kết nối. Nếu thay đổi yêu cầu hoặc quán, đưa giỏ về trạng thái cần kiểm lại.
- Hỏi bổ sung ngay ở trường thiếu hoặc mơ hồ. Nếu không tìm được giỏ phù hợp, giải thích điều kiện đang chặn và đưa người dùng về đúng chỗ có thể xử lý.
- Mỗi đơn gồm một quán và mỗi người một món. **Túi mù** là món được chọn hộ cho người nói “ăn gì cũng được” và đi qua cùng các bước kiểm.
- Hiển thị giá món, phí giao hàng chia đều và tổng từng người từ kết quả kiểm của code. Sau phản hồi đổi món, áp dụng giới hạn một lần mỗi người theo pipeline và kiểm lại giỏ.
- Chỉ hiện **Giỏ đã kiểm** khi phiên bản giỏ đang hiển thị đã qua kiểm tra. Sau khi chốt, hiển thị danh sách cuối để người đặt tự thao tác trên app giao đồ ăn.
- Gắn nhãn **Menu mẫu** ở bước chọn quán. Giá và tồn kho đến từ [dữ liệu demo](data/restaurants_sample.json). Tin nhắn là bản nháp để người đặt copy.

## Giọng điệu và thuật ngữ

Tiếng Việt tự nhiên, ngắn, ấm áp và lịch sự trong bối cảnh văn phòng. Mascot xưng “mình” khi hướng dẫn. Dùng động từ rõ trên nút. Với lỗi, nói điều gì xảy ra và chỗ cần sửa. Ví dụ “Lan còn thiếu ngân sách” hoặc “Món của Lan vượt ngân sách 3.000đ sau khi cộng phí ship”. Dùng nhất quán **ngân sách**, **phí ship/người**, **Túi mù**, **Đổi món** và **Chốt giỏ**.

## Tiêu chí nghiệm thu trải nghiệm

- Người dùng mới có thể bắt đầu bằng tin nhắn tự nhập hoặc ví dụ mẫu.
- Có thể đi từ một yêu cầu đủ dữ kiện đến giỏ cuối. Tại bước duyệt, người đặt đọc được món, giá, phần ship và tổng tiền của từng người.
- Các tình huống thiếu dữ kiện, giỏ vô nghiệm, lỗi model và đổi món lần hai đều có phản hồi cụ thể.
- Bản demo vẫn mở qua `python run.py`. `answer(text)` vẫn là điểm vào cho eval và mô phỏng chi phí. Tiêu chí đánh giá CP3 theo [spec](spec.md) và [metric đã chốt](eval/metric_spec.yaml).
