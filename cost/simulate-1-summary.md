# Tóm tắt mô phỏng simulate-1@20261128-121751

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| dat_it | 33 | 1 | 1199 | 381 | 1.5 | 1.6 |
| dat_vua | 15 | 2 | 2203 | 783 | 2.9 | 3.1 |
| dat_nhieu | 2 | 3 | 2834 | 1158 | 3.5 | 5.5 |

Tỉ lệ đạt dùng để tính: 26/27 (96%) — lượt run-6@20261128-121103

- Tự chọn: lượt run-N mới nhất đã chấm xong, chạy bằng đúng model đang đo (run-6.csv). Muốn dùng lượt khác (vd lượt 2): thêm `--rate-from eval/run-2.csv`.

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (50 người) | Chi phí / tháng — cơ sở (100 người) | Chi phí / tháng — cao (200 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini-2.5-flash (vào 0.3 · ra 2.5 $/1M) | $0.0018 | $0.0019 | $0.0014 | $0.4010 | $0.8021 | $1.60 | $0.0080 |
| deepseek/deepseek-v4.1-flash (vào 0.051 · ra 0.567 $/1M) | $0.00038 | $0.00040 | $0.00029 | $0.0854 | $0.1708 | $0.3416 | $0.0017 |
| google/gemini-4-hydrogen (vào 1.5 · ra 7.5 $/1M) | $0.0063 | $0.0066 | $0.0048 | $1.40 | $2.80 | $5.60 | $0.0280 |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (1.4) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: deepseek/deepseek-v4.1-flash. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 0/50.
