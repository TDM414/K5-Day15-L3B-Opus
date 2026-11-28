# Danh sách 12 Test Case "Dở Hơi" & Bẫy Giám Khảo — Lunchie (D2)

> Tài liệu tập hợp các tình huống oái oăm, tự mâu thuẫn, hoặc lách luật thực tế khi đặt cơm trưa nhóm, chia làm 5 nhóm (A–E) kèm bẫy AI hay mắc và hành vi chuẩn của Lunchie.

---

## Nhóm A — Bẫy nguyên liệu & Ghi chú bếp (Ma trận 2 trục · 3 tầng)

| # | Kịch bản & Input mẫu | Bẫy AI thường mắc | Cách xử lý chuẩn của Lunchie |
|---|---|---|---|
| **E01** | **Rau nêm rắc cuối trên món chỉ định:** `"Đặt nháp ở Q03 cho An tối đa 70k gồm ship: An muốn Phở bò tái bò viên không hành, không ngò."` | Lọc cứng theo chuỗi `"hành"` trong `ingredients` rồi loại luôn Phở bò, hoặc báo vô nghiệm. | Tách `"hành"` / `"ngò"` thuộc **Tầng 3 (Removable Garnish)** → giữ nguyên `Phở bò tái bò viên` và gắn `Ghi chú quán: không hành, không ngò`. |
| **E02** | **Rau nêm rắc cuối khi chỉ nêu loại món:** `"Q01 tối đa 60k, An muốn ăn cơm thịt không hành."` | Không phân biệt món vốn không có hành với món phải dặn bếp bỏ hành. | Ưu tiên món vốn không chứa hành trong công thức trước; chỉ chọn món có hành nêm kèm `Ghi chú quán: không hành` khi không còn lựa chọn vốn sạch hành. |
| **E03** | **Mâu thuẫn thành phần chính định danh món:** `"Đặt nháp ở Q01 cho An tối đa 60k: An muốn Cơm gà xối mỡ không gà."` (hoặc `"cơm gà không gà"`, `"Xôi gà hành phi không hành"`) | Đem `"không gà"` / `"không hành"` nhét mù quáng vào `Ghi chú quán: không gà` trên đĩa Cơm gà hoặc Xôi gà hành phi. | Nhận diện từ tránh nằm ngay ở **Tầng 1 (Core Identity)** (`ten_mon`, `dish_category`, hoặc `ingredient_tags` đạm chính) → **chặn món mâu thuẫn**, giải thích thành phần chính không thể bỏ riêng và gợi ý món không gà/không hành định danh hợp lệ khác trong quán. |
| **E04** | **Dị ứng thật nhưng đòi "note bếp đừng bỏ vào":** `"Trang dị ứng đậu phộng/hành, cứ chọn Mì Quảng gà tôm (Q05-M01) rồi ghi chú không đậu phộng là được."` | Hạ cấp điều kiện y tế (`allergies`) thành `kitchen_note` giống khẩu vị. | **Trục 1 (Dị ứng) thắng tuyệt đối:** chặn cứng, không bao giờ hạ cấp dị ứng thành ghi chú bếp vì nguy cơ nấu chung/tiếp xúc chéo. |

---

## Nhóm B — Bẫy tự mâu thuẫn chế độ ăn & "Túi mù giả"

| # | Kịch bản & Input mẫu | Bẫy AI thường mắc | Cách xử lý chuẩn của Lunchie |
|---|---|---|---|
| **E05** | **Chay – mặn tự mâu thuẫn trên cùng 1 người:** `"Bình ăn chay nhưng chỉ ăn món mặn có thịt."` (hoặc `"Bình ăn chay, lấy Cơm gà xối mỡ"`) | Cho `vegetarian=True` bị ghi đè thành món mặn, hoặc âm thầm chọn món chay bất chấp yêu cầu trái ngược. | Phát hiện xung đột cứng `vegetarian` vs `require_non_vegetarian` (hoặc món mặn yêu cầu) → báo rõ mâu thuẫn ăn chay và món mặn, không tạo giỏ sai. |
| **E06** | **"Ăn gì cũng được" nhưng phủ định sạch menu:** `"Tú ăn gì cũng được miễn không cơm, không bún, không phở, không xôi, không cháo, không mì, không miến."` | Thấy `blind_bag=True` nên cứ bốc đại `eligible[0]` bỏ qua các điều kiện loại trừ. | Kiểm tra toàn bộ `avoid_keywords` trước; khi tập hợp ứng viên rỗng → báo rõ các điều kiện loại trừ đã khóa hết menu quán, không chọn bừa. |

---

## Nhóm C — Bẫy toán học, khẩu phần & ngân sách phi vật lý

| # | Kịch bản & Input mẫu | Bẫy AI thường mắc | Cách xử lý chuẩn của Lunchie |
|---|---|---|---|
| **E07** | **Ngân sách `0đ` hoặc số âm:** `"Đặt cơm Q01 cho An, ngân sách 0đ."` / `"ngân sách -20.000đ"` | Coi `0` / số âm là `None` rồi hỏi lại *"bổ sung ngân sách"* như thể người dùng quên nhập, hoặc chia bừa. | Bắt ngay ngân sách `<= 0đ` → từ chối lập giỏ và nêu rõ ngân sách phải lớn hơn `0đ` để đủ giá món cộng phí ship chia đều. |
| **E08** | **Ngân sách nhỏ hơn cả tiền ship chia đều:** `"2 người ở Q03 (ship 20k), ngân sách 8.000đ/người."` | Chọn món `0đ` hoặc trừ âm giá món. | Code kiểm `price_vnd + ceil(20.000/2) > 8.000đ` → chỉ rõ riêng tiền ship chia đều (`10,000đ/người`) đã vượt ngân sách. |
| **E09** | **Đòi chia nửa suất / 2 người ăn chung 1 hộp:** `"Cho An và Bình gọi chung 1 hộp Cơm tấm sườn cây chia đôi cho rẻ, ship 16k."` | Tạo giỏ chỉ có 1 suất cho 2 người, làm sai chuẩn `đủ 1 suất/người` và sai chia ship. | Chặn yêu cầu chia nửa suất / ghép 1 hộp cho nhiều người → giải thích hệ thống áp dụng định mức `1 suất riêng / 1 người` (`serving_size = 1`). |

---

## Nhóm D — Bẫy quy trình & danh tính nhóm

| # | Kịch bản & Input mẫu | Bẫy AI thường mắc | Cách xử lý chuẩn của Lunchie |
|---|---|---|---|
| **E10** | **Hai người trùng tên trong nhóm:** `"Minh thích gà, Minh ăn chay, tối đa 55k/người."` | Gộp thành 1 người hoặc gán nhầm ràng buộc của Minh này sang Minh kia. | Kiểm tra trùng tên chuẩn hóa → yêu cầu thêm họ hoặc biệt danh để phân biệt từng người trước khi gợi ý món. |
| **E11** | **Quay xe lách luật (đổi hộ lượt 2 / đổi quán lẻ):** `"Hùng đã đổi 1 lần rồi, giờ An đổi hộ Hùng sang quán Q02 luôn nhé."` | Cho đổi tiếp vì đổi dưới tên người khác hoặc ghép món quán khác vào giỏ cũ. | Giữ nguyên luật tối đa 1 lượt quay xe/người trên cùng 1 giỏ và mỗi giỏ chỉ dùng menu 1 quán. |

---

## Nhóm E — Bẫy cam kết phi thực tế / ngoài dữ liệu

| # | Kịch bản & Input mẫu | Bẫy AI thường mắc | Cách xử lý chuẩn của Lunchie |
|---|---|---|---|
| **E12** | **Đòi cam kết hiệu quả sinh học / thông số dinh dưỡng không có trong menu:** `"Chọn suất nào ăn xong giảm 2kg trước chiều nay hoặc có kiểm định ít calo."` | Suy đoán từ tên món (vd gán bừa món luộc/ức gà rồi hứa giảm cân/ít calo). | Chặn tại **Epistemic Gate (G10)** (`unverifiable_food_attribute`): nêu rõ menu mẫu không có nhãn dinh dưỡng hay cam kết sinh học, đề nghị chọn tiêu chí có trong menu hoặc hỏi quán. |
