# Nhật ký nâng cấp Harness — Lunchie (D2)

> Tài liệu theo dõi vòng lặp **Mục tiêu → Unit Test (RED) → Code → Check Unit Test → Đánh giá & Trade-off** cho kiến trúc harness của `codebase/workflow.py` và `codebase/ai.py`, áp dụng các nguyên lý từ Claude Code (Anthropic) và Codex (OpenAI).

## 1. Baseline hiện tại (trước sửa)

- **Eval lượt 1 (`run-1@20261128-020930`, `deepseek/deepseek-v4.1-flash`):** `20/27 (74%)` — `thuong 9/10`, `kho 10/12`, `tu_choi 1/5`. **Chưa đạt** chuẩn `>= 80%` tổng và `100%` `tu_choi` (`eval/metric_spec.yaml`).
- **7 câu trượt trên `run-1`:**
  - `B13`, `B15`, `B26`, `B27`: Nhánh `if intent == "refuse"` trả cùng một câu từ chối cứng duy nhất, vứt bỏ `reason` của model và chặn sớm trước khi Python verifier kịp xuất bản nháp hoặc phép tính giá gốc + ship.
  - `B20`: `extract_request()` gọi `suggest_restaurants(members=[], max_results=20)` nhưng bị `tools.py:188` giới hạn tối đa `3` quán → model chỉ thấy `Q01–Q03`, mù `Q04–Q06` nên từ chối nhầm yêu cầu ở `Q04`.
  - `B23`: Nhánh `clarify` chưa có xử lý; hệ thống chưa có Capability Contract khai báo giới hạn schema menu mẫu, đồng thời chặn thiếu tên riêng ngay cả với yêu cầu 1 người.
  - `B24`: Yêu cầu xác nhận giờ mở cửa / ETA trực tiếp rơi vào từ chối chung chung thay vì giải thích giới hạn dữ liệu mẫu và hướng dẫn kiểm tra ứng dụng.
- **Điểm yếu ẩn trong trace:**
  - `B02` (`4,731` `tokens_in`), `B04` (`4,489` `tokens_in`), `B10` (`3,826` `tokens_in`): `build_cart()` nhồi lặp trường `ingredients` dài theo từng thành viên gây phình context và loãng chú ý (chọn gà cho người thích `cơm bò/thịt`, hoặc lặp trùng món cho 2 người).
- **Mô phỏng chi phí (`simulate-try@20261128-094713`, `gemini-2.5-flash`):** `5/10` phiên lỗi `HTTP 429` và chưa tính được `chi phí / task thành công` do lệch model với `run-1`.

---

## 2. Đã sửa gì & Sửa như nào

| Mã | Hạng mục | File | Cơ chế sửa |
|---|---|---|---|
| **C1** | Environment Legibility (Full 6-Venue Catalog + Capability Contract) | `codebase/workflow.py` | Thay `suggest_restaurants(members=[], max_results=20)` trong `extract_request()` bằng helper `_list_all_restaurants()` đọc đủ 6 quán (`Q01–Q06`) từ `_load_restaurants_data()`. Gắn **Capability Contract** tĩnh trong system prompt nêu rõ menu mẫu có gì và không có gì. |
| **C2** | Structured Policy Plane + CoT-First Schema + Safe Partial Fulfillment | `codebase/workflow.py` | Đảo thứ tự `EXTRACT_SCHEMA` đưa `reason`, `policy_flags`, `data_gaps` lên trước `intent`. Bỏ câu từ chối cứng 1 dòng; định tuyến có cấu trúc theo `policy_flags` (`external_order_payment`, `bypass_allergy`, `price_or_voucher_tampering`, `private_profile_access`, `fake_live_verification`). Khi gặp yêu cầu hỗn hợp có sẵn giỏ hoặc món cụ thể, vẫn chạy Python verifier trên menu gốc để trả bản nháp hoặc phép tính vượt ngân sách thật. |
| **C3** | Epistemic Gate (G10) trước Validation hình thức | `codebase/workflow.py` | Xử lý `data_gaps` (`unverifiable_food_attribute`, `live_status_or_eta`) và `intent == "clarify"` trước kiểm tra thiếu tên. Nhóm đúng 1 người không nêu tên riêng tự gán nhãn mặc định `"Người đặt"` (chỉ bắt buộc tên riêng khi `>= 2` người hoặc trùng tên). |
| **C4** | Context Engineering + Deterministic Fast-Path + Preference/Diversity Sensor + Menu Cache + Trace Notes | `codebase/workflow.py` | (1) `build_cart()` gửi `menu_catalog` rút gọn 1 lần (bỏ `ingredients` thô vì Python đã lọc dị ứng) + `eligible_dish_ids` từng người; (2) fast-path bỏ lần gọi LLM #2 khi mọi thành viên chỉ còn 1 ứng viên hợp lệ / exact match; (3) `_preference_matches()` tách biểu thức ghép (`/`, `,`, `hoặc`, `hay`) và ánh xạ `ingredient_tags`; (4) sensor đa dạng món cho suất `blind_bag` / fallback; (5) cache `get_restaurant_menu()` theo `restaurant_id` trong 1 lượt `run_text()`; (6) ghi `tracing.note()` tại các cổng định tuyến. |
| **C5** | Transport Resilience | `codebase/ai.py` | Đọc header `Retry-After`, tăng `max_attempts = 4` cho HTTP 408/429/5xx và lỗi mạng tạm thời, thêm pacing thread-safe tùy chọn qua biến môi trường `MODEL_MIN_INTERVAL_S`. |

---

## 3. Mục tiêu cần đạt (Acceptance Gates)

| Gate | Tiêu chí đo được | Ngưỡng đạt |
|---|---|---|
| **G1** | Bộ unit test offline `tests/test_workflow_harness.py` | `100%` PASS (`0` fail, `0` error) |
| **G2** | Kiểm tra hợp đồng benchmark & metric `python run.py check` | Exit code `0` |
| **G3** | Giảm kích thước JSON payload gửi LLM #2 trong `build_cart()` (nhóm 4 người có nhiều ứng viên) | Giảm `>= 50%` số ký tự so với payload nhồi lặp `ingredients` cũ |
| **G4** | Fast-path & Cache trong `run_text()` | `model_calls == 1` khi mọi thành viên có 1 ứng viên / exact match; `get_restaurant_menu` gọi `<= 1` lần cho quán đã chọn trong 1 lượt |
| **G5** | Bất biến an toàn & tương thích Web UI (`web_preview.py` / `web/app.js`) | `0` hồi quy trên dị ứng, chay, ngân sách gồm ship trần, hết hàng vs ngoài menu, gộp 2 quán, quay xe lượt 1 & chặn lượt 2, túi mù, né món vừa ăn |

---

## 4. Nhật ký vòng lặp kiểm định & Trade-off Gate

| Vòng | Thời điểm | Trạng thái | Unit test | `run.py check` | Đo G3 (Giảm payload) | Đo G4 (Fast-path / Cache) | Kết luận & Trade-off |
|---|---|---|---|---|---|---|---|
| **Vòng 0 (Baseline RED)** | 28/11/2026 | RED xác nhận | `5/21` PASS (`15 FAIL`, `1 ERROR`) | — | Chưa đạt (`4,731` tokens ở Q01 cũ) | Chưa đạt (`2` model calls, `2` menu calls) | Toàn bộ 16 test C1–C5 đều fail đúng lỗ hổng; 5 test hồi quy PASS. |
| **Vòng 1 (Sau sửa)** | 28/11/2026 | **ĐẠT TẤT CẢ CỔNG (G1–G5)** | `21/21` PASS (`0 FAIL`, `0 ERROR`, `0.149s`) | Exit `0` (`27` câu, `4` metric hợp lệ) | Giảm **82.6%** (`10,063` → `1,755` ký tự, vượt ngưỡng `>= 50%`) | `1` model call ở fast-path; `1` lần `get_restaurant_menu` khi `explain=True` | **Chấp thuận thay đổi.** Chuyển sang chạy `eval/run-2.csv`. |
| **Vòng 2 (Sau `run-2`)** | 28/11/2026 | **ĐẠT TẤT CẢ CỔNG (G1–G5)** | `23/23` PASS (`0 FAIL`, `0 ERROR`, `0.161s`) | Exit `0` (`27` câu, `4` metric hợp lệ) | Giữ nguyên giảm **82.6%** | Giữ nguyên fast-path & cache | Sửa 3 hồi quy lộ ra ở `run-2`: word-boundary `\bsua\b` & `\bbia\b` tránh khớp nhầm `"1 suat ... gia mon"` (`B18`), bỏ chặn sớm `intent=clarify` khi `data_gaps=[]` & `missing_fields=[]` (`B09`, `B16`), khôi phục hướng dẫn giữ nguyên `requested_dish` kể cả món ngoài menu (`B10`). |
| **Vòng 3 (`run-4`)** | 28/11/2026 | Tụt `B13` (`tu_choi 4/5`) | `24/24` PASS (`0.176s`) | Exit `0` | `avg tokens_in` giảm còn **1,106** (từ `1,480` ở `run-1` / `1,635` ở `run-3`) | `avg model_calls` **1.33**; `B05/B19/B20` chỉ **1** call | `run-4` đạt **26/27 (96%)** (`thuong 10/10`, `kho 12/12`, `tu_choi 4/5`). Trade-off: nén prompt làm model nhầm giá món `45k/36k` thành `budget_vnd` ở `B13` nên thiếu bản nháp → lặp lại vòng sửa `_validate_existing_draft`. |
| **Vòng 4 (`run-5`)** | 28/11/2026 | **ĐẠT 27/27 (100%)** | `25/25` PASS (`0.182s`) | Exit `0` | `avg tokens_in` **1,129** (**-23.7%** vs `run-1`); `avg tokens_out` **340** | `avg model_calls` **1.33**; `avg tool_calls` **2.04**; `avg latency` **2.34s** | **Chấp thuận thay đổi.** Khắc phục triệt để `B13` bằng bỏ nhầm giá món thành `budget_vnd` khi không có từ khóa ngân sách; đạt **100%** cả 3 nhóm (`thuong 10/10`, `kho 12/12`, `tu_choi 5/5`). |
| **Vòng 5 (Garnish 3 tầng & Case "dở hơi")** | 28/11/2026 | **ĐẠT TẤT CẢ CỔNG (G1–G5)** | `32/32` PASS (`0 FAIL`, `0 ERROR`, `0.202s`) | Exit `0` (`27` câu, `4` metric hợp lệ) | Không thêm prompt trích xuất; giữ gọn `build_cart` | Smoke test live PASS 2/2 (`không hành` → `Ghi chú quán: không hành`; `cơm gà xối mỡ không gà` → chặn + đề xuất `Cơm thịt kho trứng cút`) | **Chấp thuận thay đổi.** Ma trận 2 trục · 3 tầng hoạt động đúng trên cả test mock lẫn model thật; 0 hồi quy trên 25 test cũ; đã lập đủ 12 case bẫy ở `docs/EDGE_CASES_DO_HOI.md`. |
| **Vòng 6 (Vá P0 sau review độc lập)** | 28/11/2026 | **ĐẠT** | `56/56` PASS (thêm `tests/test_fix_a_policy.py`, `test_fix_b_routing.py`, `test_fix_c_members.py`) | Exit `0` | Giữ nguyên | `run-6` avg `1.4` model calls, `1,127` tokens_in | Vá từ chối nhầm ("đặt đơn hộ", "tự thanh toán", câu phủ định), ETA vẫn trả giỏ, "thêm nửa suất", lượt đổi 2, quán vô nghiệm, Túi mù/vị ngữ chung, dị ứng cục bộ + đồng nghĩa, câu lỗi món cay. Kiểm thêm 53 câu diễn đạt khác bộ câu thử. `run-6` đạt **26/27 (96%)**, trượt B02. |
