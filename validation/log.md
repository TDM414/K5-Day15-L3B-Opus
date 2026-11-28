# Người dùng thử *(bonus)*

Guide bước 4.3 · 2–3 người ngoài nhóm từng gom đơn cơm trưa cho đồng nghiệp · khoảng 10 phút/người.

Chạy `python run.py` và mở trang chủ Lunchie ở địa chỉ terminal in ra. Mở lại trang chủ cho mỗi người. Dùng đoạn chat giả lập dưới đây và để người thử tự thao tác trên máy. Nếu dịch vụ AI báo lỗi, ghi thời điểm và thông báo trong cột quan sát.

## Một phiên, 5 nhịp

1. **Làm quen (~1 phút).** “Tụi mình đánh giá sản phẩm, không đánh giá bạn. Cứ nói to suy nghĩ.”
2. **Bối cảnh (~1 phút).** “Kể lần gần nhất bạn gom đơn cơm trưa cho đồng nghiệp. Bạn đã làm gì từ lúc nhận tin nhắn đến lúc chốt món và tính tiền từng người?”
3. **Giao việc (~1 phút).** Đưa đoạn chat bên dưới và nói “Hôm nay bạn đặt cơm trưa cho ba đồng nghiệp. Dùng Lunchie để chốt một giỏ từ cùng một quán. Cuối cùng, cho mình xem mỗi người ăn gì, trả bao nhiêu sau khi cộng phí ship và danh sách bạn sẽ dùng để tự đặt.” Để người thử tự cầm chuột. Giữ tên nút và thứ tự thao tác cho người thử tự khám phá.
4. **Quan sát (~5 phút).** Im lặng ghi thao tác đầu tiên, chỗ dừng hoặc quay lại, chỗ hiểu sai, cách tự xử lý và kết quả. Nếu họ kẹt, chỉ hỏi “Bạn sẽ làm gì tiếp?” hoặc “Bạn nghĩ nó nên chạy thế nào?”. Không thuyết minh, chỉ nút hay hỏi “Bạn có thích không?”.
5. **Hỏi sau (~2 phút).** “Điều gì khó hiểu nhất?” · “Bạn có tin kết quả này không? Vì sao?” · “Bạn có dùng Lunchie thật không? Trong lần đặt cơm nào?” · “Nếu mai không được dùng nữa, bạn thấy rất tiếc, hơi tiếc hay không sao?”

### Đoạn chat đưa cho người thử

```text
Mai: Mình chỉ ăn cơm gà xối mỡ, tối đa 75k cả ship.
An: Mình ăn chay, không ăn cay, 65k cả ship.
Linh: Món nào cũng được, chọn giúp mình nhé, 70k cả ship.
```

**Mốc quan sát cho người điều phối.** Người thử phát hiện và sửa dữ kiện bị hiểu sai nếu có, chọn được một quán, chỉ ra món và tổng tiền đã gồm ship của từng người, rồi tìm được danh sách cuối để tự đặt. Ghi lại nếu họ nghĩ rằng chốt giỏ trong Lunchie đã gửi đơn cho quán.

**Bài khó hơn.** Nếu phiên chỉ thu được lời khen, đánh dấu *phiên chưa đạt* và giao thêm tình huống này. Nếu người thử đã chốt, bắt đầu một giỏ mới với cùng đoạn chat. Nếu hết giờ, dùng tình huống này cho phiên kế tiếp. Khi người thử đang xem giỏ và chưa chốt, đưa tin nhắn “An vẫn ăn chay, không cay, nhưng chỉ còn 55k cả ship.” Sau khi người thử cập nhật giỏ theo ngân sách mới, đưa tin nhắn “Linh muốn một món khác, vẫn 70k cả ship.” Yêu cầu họ chốt giỏ đã cập nhật để tự đặt.

## Nhật ký từng người

Mỗi người một dòng, dùng mã và vai trò thay cho tên. Trong cột **Quan sát**, ghi hành động và kết quả theo thứ tự đã xảy ra, kể cả câu nhắc của điều phối viên nếu có. Ghi lựa chọn *rất tiếc / hơi tiếc / không sao* trong cột **Trích nguyên văn** cùng câu nói thực tế. Nếu thiếu trích dẫn, để trống. Ưu tiên hành vi đã thấy khi kết luận. Câu “mình sẽ dùng” là bằng chứng yếu nhất.

Mức nghiêm trọng theo ảnh hưởng tới việc giao. **Cao** nếu người thử bị chặn hoặc chốt sai món, điều kiêng hay ngân sách. **Vừa** nếu phải dò hoặc làm lại đáng kể nhưng vẫn hoàn thành. **Thấp** nếu chỉ do dự ngắn và tự tiếp tục. Ghi **—** nếu chưa thấy vấn đề.

**28/11 · Ba phiên người dùng thử.** Ba người dùng thao tác độc lập trên giao diện Lunchie trên trình duyệt. Dùng menu mẫu và phản hồi model giả lập. Thao tác, trạng thái màn hình và nội dung sao chép đến từ các phiên chạy. Trích dẫn là lời nhận xét được ghi lại.

| Người thử (vai) | Việc giao | Quan sát | Trích nguyên văn | Mức nghiêm trọng |
|---|---|---|---|---|
| AI-01 (Nhân viên văn phòng) | Chốt cơm cho 3 người từ đoạn chat và lấy danh sách để tự đặt. | Bấm **Bắt đầu đặt cơm**, dán chat, kiểm yêu cầu rồi chọn Bếp Cơm Nhà Văn Phòng. Dừng để cộng lại ba suất. Tổng từng người là 145.002đ, tổng đơn là 145.000đ. Đọc được ghi chú làm tròn trên màn hình rồi tự chốt và kiểm tra danh sách đã sao chép. Bản sao có cả hai mức tiền nhưng thiếu ghi chú làm tròn. | “Quán hiện 16.000đ phí ship cho cả đơn và 5.334đ mỗi người. Tôi muốn xem giỏ cuối chia phần lẻ thế nào để thu đúng tổng.” Trả lời giả định **hơi tiếc**. | Thấp |
| AI-02 (Nhân viên văn phòng) | Chốt cơm cho 3 người từ đoạn chat và lấy danh sách để tự đặt. | Bấm **Bắt đầu đặt cơm**, dán chat, kiểm yêu cầu rồi chọn quán. Khựng ở nhãn **Túi mù**, đọc tên món và giá để hiểu rồi mở thực đơn tìm căn cứ cho yêu cầu không cay của An. Thực đơn chỉ hiện tên và giá. Tự chốt và kiểm tra danh sách đã sao chép. Tin phần giá hơn phần không cay vì đối chiếu được giá. | “Tôi hơi khựng ở chữ “Túi mù” của Linh. Món và giá đã hiện ngay bên dưới, nên tôi hiểu đó là món app chọn giúp.” Trả lời giả định **hơi tiếc**. | Thấp |
| AI-03 (Nhân viên văn phòng) | Dựng giỏ, giảm ngân sách của An xuống 55.000đ, đổi món của Linh, rồi chốt và lấy danh sách. | Bấm **Bắt đầu đặt cơm** và dựng giỏ. Từ giỏ, qua **Đổi quán** rồi **Quay lại xác nhận** để sửa ngân sách của An và dựng lại với cùng quán. Sau đó nhập yêu cầu đổi món cho Linh. Bấm **Để AI gợi ý** đã đổi món ngay và dùng lượt đổi. Vẫn tự chốt và kiểm tra danh sách đã sao chép. Tổng đơn 142.000đ, Linh đổi sang cơm gà xối mỡ 50.334đ gồm ship. | “Mình tưởng nút “Để AI gợi ý” sẽ cho xem món trước, ai ngờ bấm xong đã dùng lượt đổi.” Trả lời giả định **hơi tiếc**. | Vừa |

## Tổng hợp

- **Chủ đề lặp nhiều nhất** — Đối chiếu giỏ trước khi tự đặt. Cả 3 phiên kiểm tra bản sao sau khi chốt. Hai phiên cơ bản đều tìm thêm căn cứ trên màn hình, một phiên về phí ship và một phiên về món không cay.
- **Sửa gì trước demo** — Đề xuất thêm đường **Sửa yêu cầu** từ giỏ và cho xem món AI gợi ý trước khi xác nhận đổi. Phiên bài khó phải đi vòng để sửa ngân sách và đã dùng lượt đổi ngay khi muốn xem gợi ý. Ghi thay đổi thực hiện vào [changelog ở spec.md §10](../spec.md#10-phân-công--changelog).
- **Giữ gì và vì sao** — Giữ tổng từng suất gồm ship và nút sao chép danh sách sau khi chốt. Cả 3 phiên tự lấy được danh sách có món và giá từng người để tự đặt.
- **Để dành sau** — Làm rõ nhãn **Túi mù**, bổ sung căn cứ món không cay và đưa ghi chú làm tròn vào bản sao. Các điểm này làm chậm việc đối chiếu trong hai phiên cơ bản, cả hai vẫn hoàn thành.
