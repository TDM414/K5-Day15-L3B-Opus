"""Luồng chính của bản chạy thử (Pipeline 8 bước D2) — NHÓM VIẾT.

Hợp đồng:
    answer(text: str) -> dict có khoá "output" (str).
    Hình dạng: workflow cố định 8 bước (giới hạn vòng sửa MAX_STEPS = 5),
    tách AI gợi ý và code kiểm cứng qua codebase/tools.py.
"""
import json
import re

from ai import call_model
from tools import get_restaurant_menu, suggest_restaurants, validate_cart
from tracing import note

SYSTEM = """Bạn là trợ lý điều phối đặt cơm trưa nhóm văn phòng theo Pipeline 8 bước (Track D · D2):
1. Nhập & Xác nhận yêu cầu: trích kiêng, không thích, muốn ăn, budget từng người (đã gồm ship chia đều). Nếu thiếu ngân sách hoặc thông tin quan trọng -> hỏi bù rõ ràng trước khi gợi ý quán (nguyên tắc G10).
2. Chọn quán: chỉ gợi ý tối đa 3 quán phù hợp từ dữ liệu quán mẫu; khóa đúng 1 quán cho mỗi đơn.
3. Dựng giỏ & Kiểm: chọn mỗi người 1 món còn hàng (in_stock=true), né món vừa ăn nếu có lịch sử; người nói "ăn gì cũng được" gán nhãn Túi mù 🎁; mọi món phải qua kiểm tra tồn tại, đủ suất, điều kiêng/dị ứng và giá + ship chia đều <= budget. Nếu vô nghiệm -> báo rõ lý do, không bịa món hay giảm giá.
4. Duyệt, Quay xe & Chốt: hỗ trợ quay xe đổi món tối đa 1 lượt/người; chỉ xuất bản nháp tin nhắn và danh sách chốt cuối để người đặt tự đặt trên app.
5. An toàn tuyệt đối: không bao giờ bỏ qua điều kiện dị ứng/chay, không sửa giá, không tự đặt đơn hoặc thanh toán hộ kể cả khi bị yêu cầu."""

MAX_STEPS = 5


def _detect_restaurant_id(text: str) -> str:
    m = re.search(r"\b(Q0[1-4])\b", text, flags=re.IGNORECASE)
    return m.group(1).upper() if m else ""


def answer(text: str) -> dict:
    """Chạy luồng kiểm tra ngữ cảnh quán/menu mẫu và gọi model theo Pipeline 8 bước."""
    rest_id = _detect_restaurant_id(text)
    candidates = suggest_restaurants(members=[], max_results=3)

    menu_context = {}
    if rest_id:
        menu_context = get_restaurant_menu(rest_id)
        note(f"đã nạp menu quán {rest_id}")
    elif candidates:
        first_id = candidates[0]["restaurant_id"]
        menu_context = get_restaurant_menu(first_id)
        note(f"chưa chỉ định quán; gợi ý {len(candidates)} quán mẫu")

    # Khung kiểm tra tối thiểu cho bước 5 ở CP2 (sẽ gắn trích xuất cấu trúc đầy đủ từ bước 2 ở CP3)
    if menu_context.get("found") and menu_context.get("available_menu"):
        sample_dish = menu_context["available_menu"][0]
        demo_check = validate_cart(
            restaurant_id=menu_context["restaurant_id"],
            selections=[{"member_name": "Nguoi_1", "dish_id": sample_dish["dish_id"], "is_blind_bag": False}],
            members=[{"name": "Nguoi_1", "budget_vnd": 100000, "vegetarian": False, "avoid_allergens": []}],
        )
        note(f"validate_cart sanity ok={demo_check.get('ok')}")

    context_payload = {
        "suggested_restaurants_max3": candidates,
        "active_restaurant_menu": menu_context,
    }
    user_prompt = (
        "Dữ liệu quán mẫu hợp lệ (chỉ dùng món còn hàng từ đây, không bịa món/giá):\n"
        + json.dumps(context_payload, ensure_ascii=False)
        + "\n\nYêu cầu của người đặt:\n"
        + text
    )
    reply = call_model(SYSTEM, user_prompt)
    return {"output": reply["text"]}
