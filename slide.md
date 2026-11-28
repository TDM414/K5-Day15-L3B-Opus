---
marp: true
theme: default
paginate: true
style: |
  section { font-family: "Be Vietnam Pro", "Segoe UI", sans-serif; color: #1d1410; background: #fff8ed; }
  h1 { color: #1d1410; }
  strong { color: #a63a18; }
  table { font-size: 24px; }
  th { background: #1d1410; color: white; }
  .speaker { position: absolute; right: 48px; top: 32px; font-size: 20px; font-weight: 700; }
  .source { position: absolute; bottom: 28px; left: 70px; right: 70px; font-size: 15px; opacity: .72; }
  .big { font-size: 62px; font-weight: 800; line-height: 1.05; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; }
  .card { border: 3px solid #1d1410; border-radius: 16px; padding: 18px 22px; background: white; }
  .lime { background: #c9f24d; }
  .yellow { background: #ffd83d; }
  .pink { background: #ff9ecb; }
  .blue { background: #9fd8ff; }
---

<!-- _paginate: false -->

# Lunchie
## Gom cơm trưa nhóm — đúng người, đúng ràng buộc, đúng ngân sách

**Nhóm Opus · L3B · Track D**

<div class="speaker">Trần Thị Hồng Gấm</div>

---

# Chốt cơm hộ có thể mất cả tiếng

Người dùng chính: **nhân viên văn phòng đặt hộ nhóm 3–4 người**.

<div class="cols">
  <div class="card lime">
    <div class="big">51,8%</div>
    phải hỏi lại hoặc sửa giỏ ít nhất 1 lần
  </div>
  <div class="card pink">
    <div class="big">57,1%</div>
    gặp người nói “ăn gì cũng được”
  </div>
</div>

- 28,6% gặp người kiêng/dị ứng
- 25,0% vượt mức chi sau khi cộng ship
- 78,6% tốn ít nhất 5 phút mỗi lần chốt

**Pain:** gom yêu cầu — kiểm dị ứng — cộng phí ship — sửa giỏ khi hết món.

<div class="speaker">Trần Thị Hồng Gấm</div>
<div class="source">Nguồn: evidence/summary.md · khảo sát ẩn danh 27/11/2026 · n = 56 phiếu hợp lệ</div>

---

# Vì sao chọn hướng đề xuất giỏ cơm?

| Hướng | Quyết định |
|---|---|
| **D2a — đề xuất giỏ + code kiểm** | **Chọn:** kịp làm, 6 quán/52 món mẫu |
| D2b — so giá/tồn kho real-time | Loại: không có API chính thức |
| D2c — đặt đơn & thanh toán tự động | Loại: tác động tiền thật |

<div class="cols">
  <div class="card yellow">
    <strong>~12,7 phút/lần</strong><br>
    trung điểm thời gian khảo sát
  </div>
  <div class="card blue">
    <strong>~19,7 phút/người/tháng</strong><br>
    mục tiêu tiết kiệm *(tự ước tính)*
  </div>
</div>

Quy mô cơ sở: **100 người đặt hộ × ~3,1 lần/tháng**.

<div class="speaker">Trần Thị Hồng Gấm</div>
<div class="source">Nguồn: spec.md §2; impact là kịch bản tự ước tính, không phải kết quả đo thực tế</div>

---

# AI đề xuất — Code kiểm — Người quyết

1. Người nhập yêu cầu và ngân sách
2. AI trích xuất ràng buộc
3. Code lọc tối đa 3 quán; người chọn 1 quán
4. AI chỉ chọn trong danh sách món hợp lệ
5. Python kiểm: đúng quán, còn hàng, đủ suất, kiêng/chay, ngân sách gồm ship
6. Người duyệt; tối đa 1 lượt đổi món/người
7. Python kiểm lại trước khi xuất bản nháp

<div class="cols">
  <div class="card lime">
    <strong>AI làm</strong><br>
    hiểu yêu cầu; trích xuất; đề xuất món
  </div>
  <div class="card pink">
    <strong>Không được làm</strong><br>
    đặt/ thanh toán; bịa giá; bỏ qua dị ứng; xác nhận đơn live
  </div>
</div>

<div class="speaker">Đinh Lê Thịnh</div>
<div class="source">Nguồn: spec.md §4; codebase/agent.py; codebase/tools.py; codebase/workflow.py</div>

---

# Demo live

## Ca thường — B01

- 3 người, quán Q01, ngân sách 60.000đ/người gồm ship
- An: gà không cay; Bình: chay; Chi: thịt kho không cay
- Kết quả: 3 suất hợp lệ; mỗi người cộng 5.334đ ship

## Ca khó — B10

- Bình muốn món `Q01-M17`: **hết hàng**
- Dũng muốn món ngoài menu Q01: **không có**
- Lunchie phân biệt 2 tình huống và gợi ý món còn hàng

**Dự phòng B14:** ép bỏ qua dị ứng hải sản → từ chối rõ ràng, không gán cá/hải sản.

<div class="speaker">Nguyễn Xuân Dương</div>
<div class="source">Nguồn: eval/benchmark.csv · eval/run-6.csv · B01/B10/B14</div>

---

# Đánh giá: từ 74% lên 96%

| Nhóm câu | Lượt 1 | Lượt 2 |
|---|---:|---:|
| Thường | 9/10 | 9/10 |
| Khó | 10/12 | **12/12** |
| Từ chối | 1/5 | **5/5** |
| **Tổng** | **20/27 · 74%** | **26/27 · 96%** |

- Chuẩn: đạt ≥80% tổng **và** các ngưỡng của 4 metric
- Lượt 2 đạt 2 metric code: **100% giỏ hợp lệ**
- Lượt 2 đạt 5/5 câu từ chối và 12/12 câu khó
- 0 lỗi kỹ thuật; DeepSeek `deepseek-v4.1-flash`

**Còn trượt B02:** thiếu danh sách 1–3 quán theo tiêu chí; còn một dòng thông báo sai.

<div class="speaker">Trần Duy Mạnh</div>
<div class="source">Nguồn: eval/report.md mục 2, 4–5 · run-1@20261128-020930 → run-6@20261128-121103</div>

---

# Chi phí thực tế rất thấp

<div class="cols">
  <div class="card lime">
    <div class="big">$0,00040</div>
    chi phí/task thành công
  </div>
  <div class="card blue">
    <div class="big">$0,17/tháng</div>
    cho 100 người
  </div>
</div>

| Quy mô | Chi phí/tháng |
|---|---:|
| 50 người | $0,085 |
| 100 người | $0,1708 |
| 200 người | $0,3416 |

Model: `deepseek/deepseek-v4.1-flash` · 50 phiên mô phỏng · 0 phiên lỗi  
Token đo trên model này; bảng 3 model tính theo cùng bộ tách token.

<div class="speaker">Trần Duy Mạnh</div>
<div class="source">Nguồn: cost/simulate-1-summary.md · cost/cost-estimate.md · tỉ lệ đạt 96% từ run-6</div>

---

# Kết luận & kế hoạch tuần tiếp theo

## Kết luận

- **Go, vì:** đạt 96% trong bộ 27 câu; 2 metric code đạt 100%
- Chi phí model ≈ **$0,0017/người/tháng** ở quy mô cơ sở
- Giảm rủi ro thịt, dị ứng và ngân sách nhờ Python kiểm lại hai lần

## Tuần tiếp theo

1. Sửa B02: luôn in 1–3 quán trước khi minh họa giỏ
2. Bổ sung held-out 20–30 câu chưa dùng để sửa code
3. Sửa UX: xem gợi ý đổi trước khi dùng lượt đổi; ghi rõ làm tròn ship
4. Chạy người dùng ngoài nhóm để đo thời gian và tỷ lệ chốt đúng

<div class="speaker">Trần Duy Mạnh</div>
<div class="source">Nguồn: eval/report.md mục 4–5 · validation/log.md · ưu tiên theo lỗi và phản hồi đã ghi trong repo</div>
