# AI SPEC — D2: Đặt đơn cơm trưa nhóm có ràng buộc ăn uống · Nhóm Opus · Lớp L3B · Track D

> Mốc nộp: §7 chốt chuẩn "đạt" tại **CP2 19:30 Thứ Sáu 27/11** · §0–§7 nộp **CP3 10:00 Thứ Bảy 28/11** · đủ §0–§10 **CP4 14:30 Thứ Bảy 28/11** · §10 changelog ghi tiếp đến **23:59 Thứ Bảy 28/11**.
> Đầu mỗi mục ghi bước guide (`02-guide.md` trong repo đề) chỉ cách điền. Mỗi mục ngắn, có số và nguồn; chi tiết để ở file được trỏ tới.

Track: [ ] A · [ ] B · [ ] C · [x] D · [ ] E — bài toán: D2 — Đặt đơn nhóm có ràng buộc ăn uống (nhóm tự cụ thể hóa cho bữa trưa văn phòng từ menu 1 quán, có chia đều phí giao hàng và chế độ chọn hộ)
Data BTC cấp đã dùng (nếu có — không commit nguyên file): Không dùng data BTC; nhóm tự chuẩn bị menu mẫu từ bộ món ăn Việt công khai (xem `data/DATA_CARD.md`).

## §0. Hiện tại việc này diễn ra thế nào *(guide 1.1)*
- Luồng hiện tại của việc này, trên quy trình gom đơn thực tế (4 bước, nguồn khảo sát `evidence/survey/results_valid.csv`, n = 56):
  1. Người được giao đặt hộ hỏi món cả nhóm qua link đặt đơn nhóm Grab/ShopeeFood (`21/56 = 37.5%`), hỏi trực tiếp bằng miệng (`17/56 = 30.4%`) hoặc nhắn nhóm chat Zalo/Slack/Teams (`13/56 = 23.2%`).
  2. Thu thập mức chi, điều kiện kiêng/dị ứng và tự xử lý khi có người nói *"ăn gì cũng được"* (`32/56 = 57.1%`).
  3. Đối chiếu menu một quán trên app đặt đồ ăn, cộng giá món với phí giao hàng chia đều (`38/56 = 67.9%` chia đều ship vào ngân sách từng người) để kiểm tra mức chi.
  4. Hỏi lại hoặc sửa giỏ (`29/56 = 51.8%` phải hỏi lại/sửa giỏ ít nhất 1 lần) khi quán hết món, vượt ngân sách hoặc người chưa chọn món rồi mới bấm đặt.
- Công cụ / AI đang được dùng cho việc này + nguồn: Chủ yếu thực hiện thủ công kết hợp tính năng *Đặt đơn nhóm (Group Order)* trên GrabFood/ShopeeFood (`21/56 = 37.5%`, nguồn `evidence/survey/results_valid.csv`); chưa ghi nhận công cụ AI chuyên biệt cho bước gom ràng buộc ăn uống + chia phí giao hàng (`chưa kiểm` ngoài tập khảo sát).

## §1. Người dùng & bằng chứng *(guide 1.1, 1.2)*
- Người dùng chính (một vai cụ thể): Nhân viên văn phòng được giao đặt các suất cơm trưa riêng trong cùng một đơn cho nhóm đồng nghiệp (≥ 3 người, phổ biến nhất nhóm 3–4 người: `41/56 = 73.2%`).
- Việc họ cố làm xong (`động từ + đối tượng + bối cảnh`, không có chữ AI): Chốt một giỏ gồm các suất cơm trưa riêng từ menu một quán cho nhóm đồng nghiệp vào giờ trưa, thỏa mãn đồng thời điều kiện ăn uống, sở thích và ngân sách từng người đã gồm phí giao hàng.
- Hôm nay họ giải bằng gì, hỏng ở đâu, vì sao chưa bỏ: Giải bằng hỏi miệng (`30.4%`), nhóm chat (`23.2%`) hoặc link đặt đơn nhóm trên app (`37.5%`). Hỏng khi có người nói *"ăn gì cũng được"* (`32/56 = 57.1%`), quán hết món phải đổi (`25/56 = 44.6%`), người kiêng/dị ứng (`16/56 = 28.6%`) hoặc vượt mức chi sau khi cộng phí ship (`14/56 = 25.0%`), dẫn tới phải hỏi lại/sửa giỏ (`29/56 = 51.8%`). Chưa bỏ vì đây là thói quen sẵn có ngay trên app đặt đồ ăn, không phải cài thêm công cụ.
- Pain (KHÔNG chữ AI): Người đặt cơm trưa hộ nhóm đồng nghiệp phải hỏi và đối chiếu mức chi, điều kiện ăn uống và xử lý yêu cầu "ăn gì cũng được" với menu quán rồi chia phí giao hàng — bị vướng ở khâu hỏi lại và sửa giỏ nhiều lượt (`29/56 = 51.8%`) — hậu quả là tốn `5–30+ phút` để chốt đơn (`44/56 = 78.6%` tốn ≥ 5 phút; `17/56 = 30.4%` tốn ≥ 15 phút) và có nguy cơ chọn món vượt mức chi hoặc không hợp điều kiện ăn uống.
- Bằng chứng — số chính + kết luận (chi tiết: `evidence/summary.md`): Khảo sát ẩn danh ngày 27/11/2026 (`evidence/survey/results_valid.csv`, **n = 56** người đúng vai / 127 tổng phiếu): `37/56 (66.1%)` gặp ≥ 1 trong 3 vướng mắc lõi D2 (ăn gì cũng được `57.1%`, kiêng/dị ứng `28.6%`, vượt mức chi sau ship `25.0%`); `29/56 (51.8%)` phải hỏi lại hoặc sửa giỏ; `38/56 (67.9%)` chia đều phí ship vào ngân sách từng người; `29/56 (51.8%)` chọn hộ thành công cho người "ăn gì cũng được" (`4/56 = 7.1%` bị đổi ý). Kết luận: pain và nhu cầu chọn hộ có thật rõ ràng; tiếp tục phỏng vấn ≥ 3 người ngoài nhóm trước CP3 để kiểm chéo nguyên nhân sâu.

## §2. Impact & quyết định chọn *(guide 1.3)*

| Hướng | Bao nhiêu người gặp | Bao nhiêu lần / tháng | Mỗi lần tốn gì | Impact / tháng | Làm kịp không | Chọn? |
|---|---|---|---|---|---|---|
| **D2a — Đề xuất giỏ suất cơm trưa riêng từ menu 1 quán (theo ngân sách gồm ship chia đều, kiêng/dị ứng, chọn hộ) + code kiểm ràng buộc** | ~1.000 người đặt hộ *(tự ước tính quy mô nhóm văn phòng mục tiêu)* | ~3.1 lần/tháng *(trung điểm Q2 khảo sát n=56)* | ~12.7 phút/lần *(trung điểm Q5 khảo sát n=56; mục tiêu rút 5–8 phút)* | ~39.370 phút/tháng (~656 giờ/tháng) trên 1.000 người | **Kịp** (menu 1 quán chuẩn hóa + code kiểm ràng buộc) | **Chọn** |
| **D2b — Tự động tìm quán & so sánh giá đa quán real-time trên app giao đồ ăn** | ~1.000 người *(tự ước tính)* | ~3.1 lần/tháng | ~15–20 phút/lần *(tự ước tính)* | Cao nhưng phụ thuộc tồn kho real-time | Không kịp (không có API công khai, rủi ro vi phạm điều khoản crawl) | Loại |
| **D2c — Tự động đặt đơn, thanh toán & chia tiền nhắc nợ sau bữa ăn** | ~1.000 người *(tự ước tính)* | ~3.1 lần/tháng | ~5–10 phút/lần *(tự ước tính)* | Trung bình | Không kịp & rủi ro tài chính cao (tác động ra ngoài) | Loại |

- **Impact / tháng** của hướng chọn = `1.000` người *(tự ước tính quy mô văn phòng mục tiêu)* × `3.1` lần/tháng *(ước lượng trung điểm Q2 khảo sát n=56: 33×1.5 + 18×4 + 2×8 + 3×12 ÷ 56 ≈ 3.1)* × `12.7` phút/lần *(ước lượng trung điểm Q5 khảo sát n=56: 12×3 + 27×10 + 15×22.5 + 2×35 ÷ 56 ≈ 12.7)* = **`~39.370 phút/tháng`** (trung bình **~39.4 phút/người/tháng** cho việc gom và chốt đơn; nếu giải pháp giúp giảm 50% thời gian chốt giỏ thì tiết kiệm **~19.7 phút/người/tháng** *(tự ước tính mức cải thiện mục tiêu)*).
- Hướng ĐÃ LOẠI + vì sao (giữ lại, đừng xoá):
  - **D2b (tìm & so sánh đa quán real-time):** không có API giá/tồn kho chính thức từ GrabFood/ShopeeFood, dễ bịa giá/hết món và không kịp làm trong thời gian hackathon.
  - **D2c (tự động đặt đơn & thanh toán):** có tác động ra ngoài (tiền bạc thật); sai sót thanh toán gây thiệt hại trực tiếp cho người đặt hộ.
- Số lần / tháng của từng kiểu người dùng (dùng cho persona ở §8, nguồn Q2 khảo sát `evidence/survey/results_valid.csv`, n = 56):
  - `dat_it` (1–2 lần/tháng): `33/56 (58.9%)` — trung bình `1.5` lần/tháng.
  - `dat_vua` (3–5 lần/tháng): `18/56 (32.1%)` — trung bình `4.0` lần/tháng.
  - `dat_nhieu` (≥ 6 lần/tháng; gồm 6–10 lần `2/56` và >10 lần `3/56`): `5/56 (8.9%)` — trung bình `10.4` lần/tháng.

## §3. Giải pháp tương tự *(guide 2.1)*
- [sản phẩm / tính năng gần giống]: một điều đáng học · một điều đáng né · mình khác gì

## §4. Thiết kế *(guide 2.2, 3.2)*
- **Lát cắt MỘT CÂU** (1 người dùng · 1 việc · 1 quyết định AI · 1 kết quả):
- Không làm (≥3 điều):
- **Sơ đồ** (ảnh / Mermaid / draw.io): [chèn ở đây]
- **Hình dạng:** [ ] workflow cố định · [ ] một agent · [ ] nhiều agent — 2 dòng lý do, và vì sao **không** chọn hình dạng phức tạp hơn:
- **AI dựa vào đâu** — mỗi công cụ (khớp `codebase/tools.py`):

  | Công cụ | Input | Output | Tác động ra ngoài? |
  |---|---|---|---|
  |  |  |  |  |

- **Mức tự động:** [ ] AI gợi ý, người quyết · [ ] AI tự làm khi chắc, chuyển người khi không · [ ] AI tự làm — lý do (sai thì ai chịu gì, sửa đắt hay rẻ):
- **Chỗ chặn rủi ro** (rủi ro lớn nhất của lát cắt bị chặn ở đâu, bằng gì):
- **Chỗ người duyệt** (việc AI không được tự làm):
- **Nguyên tắc thiết kế** (≥3, bắt buộc G10):

  | Nguyên tắc | Chỗ cụ thể trên sơ đồ / trong bản chạy thử |
  |---|---|
  | G10 — thu hẹp phạm vi khi không chắc |  |
  |  |  |
  |  |  |

- Phần nào còn giả (công cụ trả dữ liệu giả, model chế độ giả…) — ghi rõ, không giả làm thật:

## §5. Chỗ khó — 4 lớp + ≥6 kịch bản + 2 tấn công *(guide 2.3)*

| Kịch bản | Lớp (1–4) | Hành vi mong muốn (nói gì, hiện gì, cho làm gì tiếp) | Câu thử |
|---|---|---|---|
|  |  |  |  |
| *(tấn công)* |  |  |  |
| *(tấn công)* |  |  |  |

(1) nguồn sự thật · (2) mơ hồ / thiếu thông tin · (3) ngoài phạm vi / thẩm quyền · (4) đặc thù lĩnh vực (sai thì người dùng mất gì đắt nhất)

## §6. Bốn đường đi của trải nghiệm
- Mọi thứ suôn sẻ: · Không chắc (lớp 2): · Không có căn cứ (lớp 1): · Người dùng sửa:
- Bị đòi ngoài phạm vi (lớp 3): · Trường hợp đặc thù lĩnh vực (lớp 4):

## §7. Đánh giá & chuẩn "đạt" *(guide 2.4, 4.1)*
- Data card: `data/DATA_CARD.md` · bộ câu thử: `eval/benchmark.csv` — __ câu (thuong __ · kho __ · tu_choi __) · metric: `eval/metric_spec.yaml` (__ metric)
- **Chuẩn "đạt"** (chốt **trước 19:30 Thứ Sáu 27/11**, giữ nguyên đến 23:59 Thứ Bảy 28/11): "Đạt khi ≥ __% câu qua, và __"
- Kết quả: lượt 1 __/__ (__%) · lượt 2 __/__ (__%) — run ID: __ / __ → chi tiết `eval/report.md`, hồ sơ `eval/README.md`

## §8. Chi phí khi dùng thật *(guide 4.2)*
- Persona + giá: `cost/personas.yaml` · lượt mô phỏng: `cost/simulate-__.csv` (__ phiên)
- Chi phí / task thành công: __ (model __) · __ (model __)
- Chi phí / tháng ở quy mô thật: thấp __ · cơ sở __ · cao __ → chi tiết `cost/cost-estimate.md`
- So với impact / người / tháng (§2): đáng làm không, vì sao:

## §9. Rủi ro & an toàn
- Dữ liệu: đã ẩn danh gì, không thu gì, không đưa gì vào model gói miễn phí:
- AI **không được** làm gì kể cả khi người dùng yêu cầu:
- Ai có thể bị hại nếu AI sai, và nhóm chặn thế nào:

## §10. Phân công & changelog
- Phân công có tên (theo chặng, chia cặp — guide "Cách chia việc"): __
- Dùng AI vào việc gì (2–3 dòng; chi tiết `docs/ai-usage.md`):
- Nhật ký thay đổi — **mọi thay đổi sau CP2 19:30 Thứ Sáu 27/11 phải có dòng ở đây**:

**CP2 → CP4** (vd thu hẹp lát cắt, hỏi thêm người dùng, lần cải tiến trước lượt 2)

| Thời điểm | Đổi gì | Vì sao (trỏ về câu thử / lỗi / bằng chứng nào) |
|---|---|---|
|  |  |  |

**Sau CP4 (đến 23:59 Thứ Bảy 28/11)** (sửa theo góp ý — không sửa chuẩn "đạt", câu thử, số bằng chứng, kết quả các lượt đã chạy)

| Thời điểm | Đổi gì | Vì sao |
|---|---|---|
|  |  |  |
