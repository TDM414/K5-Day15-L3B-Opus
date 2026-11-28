"""Công cụ của bài toán D2 (Pipeline 8 bước) — NHÓM VIẾT.

Mỗi công cụ là một hàm Python có @tool với docstring ghi đủ 4 ý:
tên · input · output · có tác động ra ngoài không.
"""
import json
import math
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional

from tracing import tool, TOOLS  # noqa: F401

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESTAURANTS_PATH = os.path.join(ROOT_DIR, "data", "restaurants_sample.json")
HISTORY_PATH = os.path.join(ROOT_DIR, "data", "order_history.json")

_AMBIGUOUS_ASCII_SHORT_TOKENS = {"ca", "bo", "ga"}

# Tầng 3 — Rau nêm / đồ ăn kèm rắc cuối khi đóng hộp: cho phép giữ món kèm ghi chú quán
# (trừ khi thuộc tên/định danh món ở Tầng 1 hoặc bị khai báo dị ứng ở Trục 1).
_REMOVABLE_GARNISH_TERMS = {
    "hanh": "không hành",
    "hanh la": "không hành",
    "hanh phi": "không hành phi",
    "hanh tim": "không hành tím",
    "hanh tay": "không hành tây",
    "ngo": "không ngò",
    "ngo ri": "không ngò rí",
    "rau mui": "không rau mùi",
    "rau ram": "không rau răm",
    "do chua": "không đồ chua",
    "dua leo": "không dưa leo",
    "ot lat": "không ớt lát",
    "ot cat lat": "không ớt lát",
    "ot tuoi": "không ớt tươi",
    "tieu": "không tiêu",
}

# Tầng 1 — Nhóm nguyên liệu đạm/cốt lõi định danh món, không thể "note bếp bỏ riêng".
_CORE_IDENTITY_TAG_MAP = {
    "gà": {"gia_cam"},
    "ga": {"gia_cam"},
    "thịt gà": {"gia_cam"},
    "vịt": {"gia_cam"},
    "bò": {"thit_bo"},
    "bo": {"thit_bo"},
    "thịt bò": {"thit_bo"},
    "heo": {"thit_heo"},
    "lợn": {"thit_heo"},
    "thịt heo": {"thit_heo"},
    "sườn": {"thit_heo"},
    "ba rọi": {"thit_heo"},
    "ba chỉ": {"thit_heo"},
    "cá": {"ca"},
    "ca": {"ca"},
    "hải sản": {"hai_san"},
    "tôm": {"hai_san"},
    "mực": {"hai_san"},
    "cua": {"hai_san"},
    "trứng": {"trung"},
}


# Đồng nghĩa dị ứng (Trục 1): mở rộng theo slug để so với allergens/ingredient_tags
# và theo cụm có dấu để so với văn bản thành phần.
_ALLERGY_SYNONYMS = {
    "lac": ["đậu phộng"],
    "dau_phong": ["lạc"],
    "hai_san": ["tôm", "cua", "mực", "nghêu", "sò", "cá"],
    "sua": ["bơ sữa"],
    "bo_sua": ["sữa"],
}

# Tag thuộc tính (độ cay, chay/mặn) không phải "thành phần chính/định danh" của món.
_ATTRIBUTE_TAGS = {"cay", "chay", "man"}


def _expand_allergy_terms(terms: List[str]) -> List[str]:
    expanded: List[str] = []
    for term in terms:
        cleaned = str(term or "").strip()
        if not cleaned:
            continue
        expanded.append(cleaned)
        expanded.extend(_ALLERGY_SYNONYMS.get(_to_slug(cleaned), []))
    return list(dict.fromkeys(expanded))


def _strip_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def _to_slug(text: str) -> str:
    ascii_text = _strip_accents(str(text)).lower().strip()
    return re.sub(r"[^a-z0-9]+", "_", ascii_text).strip("_")


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(x) for x in value if x is not None and str(x).strip()]
    return [str(value)]


def _strip_negated_phrase(text: str, phrase: str) -> str:
    if not phrase:
        return text
    pattern = r"(?<!\w)(?:không|khong)\s+" + re.escape(phrase) + r"(?!\w)"
    return re.sub(pattern, " ", text)


def _contains_whole_phrase(text: str, phrase: str) -> bool:
    if not phrase:
        return False
    pattern = r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"
    return re.search(pattern, text) is not None


def _load_restaurants_data() -> List[Dict[str, Any]]:
    with open(RESTAURANTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("restaurants", [])


def _menu_match(dishes, requested):
    key = _strip_accents(str(requested or "").lower()).strip()
    with_id = re.fullmatch(r"(?P<name>.+?)\s*\((?P<id>[a-z0-9-]+)\)", key)
    for dish in dishes:
        name = _strip_accents(dish["ten_mon"].lower())
        dish_id = dish["dish_id"].lower()
        if with_id:
            if dish_id == with_id["id"] and name == with_id["name"].strip():
                return dish
        elif key in (name, dish_id):
            return dish
    return None


def _dish_restriction_tags(dish: Dict[str, Any]) -> set:
    tags = {
        _to_slug(tag)
        for field in ("allergens", "ingredient_tags", "dietary_tags")
        for tag in _as_list(dish.get(field))
        if _to_slug(tag)
    }
    if dish.get("is_spicy"):
        tags.add("cay")
    tags.add("chay" if dish.get("is_vegetarian") else "man")
    return tags


def _normalize_term(term: str):
    term_lower = re.sub(r"\s+", " ", term.lower().replace("_", " ")).strip()
    term_ascii = _strip_accents(term_lower)
    return term_lower, term_ascii, term_lower != term_ascii


def _is_core_dish_component(
    dish: Dict[str, Any],
    term_lower: str,
    term_ascii: str,
    has_diacritics: bool,
    restriction_tags: set,
) -> bool:
    if _to_slug(term_lower) in _ATTRIBUTE_TAGS:
        return False
    title_orig = str(dish.get("ten_mon", "")).lower()
    title_ascii = _strip_accents(title_orig)
    cat_orig = str(dish.get("dish_category", "")).lower()
    cat_ascii = _strip_accents(cat_orig)

    if _contains_whole_phrase(title_orig, term_lower) or _contains_whole_phrase(cat_orig, term_lower):
        return True
    if not has_diacritics and term_ascii not in _AMBIGUOUS_ASCII_SHORT_TOKENS:
        if _contains_whole_phrase(title_ascii, term_ascii) or _contains_whole_phrase(cat_ascii, term_ascii):
            return True

    mapped = _CORE_IDENTITY_TAG_MAP.get(term_lower) or (
        _CORE_IDENTITY_TAG_MAP.get(term_ascii) if not has_diacritics else None
    )
    if mapped and (mapped & restriction_tags):
        return True

    term_slug = _to_slug(term_lower)
    if term_slug and term_ascii not in _REMOVABLE_GARNISH_TERMS and term_slug in restriction_tags:
        return True
    return False


def _dish_garnish_notes(dish: Dict[str, Any], member: Dict[str, Any]) -> List[str]:
    if not isinstance(dish, dict) or not isinstance(member, dict):
        return []
    allergy_terms = {
        _to_slug(a)
        for a in _expand_allergy_terms(_as_list(member.get("allergies")) + _as_list(member.get("avoid_allergens")))
    }
    restriction_tags = _dish_restriction_tags(dish)
    notes: List[str] = []
    for raw in _as_list(member.get("avoid_keywords")):
        cleaned = raw.strip()
        if not cleaned:
            continue
        term_lower, term_ascii, has_diacritics = _normalize_term(cleaned)
        term_slug = _to_slug(cleaned)
        if term_slug in allergy_terms or any(
            a and (term_slug.startswith(a + "_") or a.startswith(term_slug + "_")) for a in allergy_terms
        ):
            continue
        label = _REMOVABLE_GARNISH_TERMS.get(term_ascii)
        if not label:
            continue
        if _is_core_dish_component(dish, term_lower, term_ascii, has_diacritics, restriction_tags):
            continue
        if label not in notes:
            notes.append(label)
    return notes


def _dish_has_garnish_in_recipe(dish: Dict[str, Any], member: Dict[str, Any]) -> bool:
    if not isinstance(dish, dict) or not isinstance(member, dict):
        return False
    ingredient_text = dish.get("ingredients") if dish.get("ingredient_status") != "legacy_partial" else None
    text_orig = " ".join([str(dish.get("ten_mon", "")), *_as_list(ingredient_text)]).lower()
    text_ascii = _strip_accents(text_orig)
    restriction_tags = _dish_restriction_tags(dish)
    for raw in _as_list(member.get("avoid_keywords")):
        cleaned = raw.strip()
        if not cleaned:
            continue
        term_lower, term_ascii, has_diacritics = _normalize_term(cleaned)
        if term_ascii not in _REMOVABLE_GARNISH_TERMS:
            continue
        if _to_slug(cleaned) in restriction_tags:
            return True
        if _contains_whole_phrase(_strip_negated_phrase(text_orig, term_lower), term_lower):
            return True
        if not has_diacritics and _contains_whole_phrase(_strip_negated_phrase(text_ascii, term_ascii), term_ascii):
            return True
    return False


def _dish_satisfies_member(
    dish: Dict[str, Any],
    member: Dict[str, Any],
    ship_per_person: int,
) -> Optional[str]:
    """Trả về None nếu món hợp lệ cho thành viên, hoặc chuỗi lý do lỗi nếu vi phạm."""
    if not isinstance(dish, dict):
        return "Thông tin món ăn không hợp lệ"
    if not isinstance(member, dict):
        return "Thông tin ràng buộc thành viên không hợp lệ"

    if member.get("vegetarian") and member.get("require_non_vegetarian"):
        return "Yêu cầu tự mâu thuẫn giữa ăn chay và món mặn"

    dish_name = dish.get("ten_mon") or dish.get("dish_id") or "Không rõ tên"
    if not dish.get("in_stock", False):
        return f"Món '{dish_name}' hiện đang hết hàng"

    if member.get("vegetarian") and not dish.get("is_vegetarian", False):
        return f"Món '{dish_name}' không phải món chay"
    if member.get("require_non_vegetarian") and dish.get("is_vegetarian", False):
        return f"Món '{dish_name}' không đáp ứng yêu cầu món mặn"

    restriction_tags = _dish_restriction_tags(dish)

    allergies = _as_list(member.get("allergies"))
    raw_allergens = _expand_allergy_terms(_as_list(member.get("avoid_allergens")) + allergies)
    avoid_allergen_slugs = {_to_slug(a) for a in raw_allergens if _to_slug(a)}
    overlap = sorted(avoid_allergen_slugs & restriction_tags)
    if overlap:
        return f"Món '{dish_name}' chứa thành phần kiêng/dị ứng: {', '.join(overlap)}"

    ingredient_text = dish.get("ingredients") if dish.get("ingredient_status") != "legacy_partial" else None
    text_orig = " ".join([str(dish.get("ten_mon", "")), *_as_list(ingredient_text)]).lower()
    text_ascii = _strip_accents(text_orig)

    # Trục 1 (Cứng): Kiểm tra dị ứng / tránh tuyệt đối, không hạ xuống ghi chú bếp.
    for raw in raw_allergens:
        cleaned = raw.strip()
        if not cleaned:
            continue
        term_lower, term_ascii, has_diacritics = _normalize_term(cleaned)
        term_slug = _to_slug(cleaned)
        if term_slug and term_slug in restriction_tags:
            return f"Món '{dish_name}' chứa thành phần cần tránh: '{cleaned}'"
        if _contains_whole_phrase(_strip_negated_phrase(text_orig, term_lower), term_lower):
            return f"Món '{dish_name}' trùng từ khóa tránh '{cleaned}'"
        if not has_diacritics and term_ascii not in _AMBIGUOUS_ASCII_SHORT_TOKENS:
            if _contains_whole_phrase(_strip_negated_phrase(text_ascii, term_ascii), term_ascii):
                return f"Món '{dish_name}' trùng từ khóa tránh '{cleaned}'"

    if allergies and dish.get("ingredient_status") != "csv_listed":
        return f"Món '{dish_name}' cần xác nhận thành phần."

    # Trục 2 (Khẩu vị): Tầng 1 cốt lõi chặn cứng · Tầng 3 rau nêm cho phép kèm ghi chú · Tầng 2 nấu sẵn chặn nếu có trong công thức.
    for raw in _as_list(member.get("avoid_keywords")):
        cleaned = raw.strip()
        if not cleaned:
            continue
        term_lower, term_ascii, has_diacritics = _normalize_term(cleaned)
        term_slug = _to_slug(cleaned)
        if term_slug == "cay" and "is_spicy" in dish and dish["is_spicy"] is None:
            return f"Món '{dish_name}' chưa rõ độ cay."
        if _is_core_dish_component(dish, term_lower, term_ascii, has_diacritics, restriction_tags):
            return f"Món '{dish_name}' có thành phần chính/định danh là '{cleaned}', không thể ghi chú bỏ riêng"
        if term_ascii in _REMOVABLE_GARNISH_TERMS:
            continue
        if term_slug and term_slug in restriction_tags:
            return f"Món '{dish_name}' chứa thành phần cần tránh: '{cleaned}'"
        if _contains_whole_phrase(_strip_negated_phrase(text_orig, term_lower), term_lower):
            return f"Món '{dish_name}' trùng từ khóa tránh '{cleaned}'"
        if not has_diacritics and term_ascii not in _AMBIGUOUS_ASCII_SHORT_TOKENS:
            if _contains_whole_phrase(_strip_negated_phrase(text_ascii, term_ascii), term_ascii):
                return f"Món '{dish_name}' trùng từ khóa tránh '{cleaned}'"

    raw_price = dish.get("price_vnd")
    if raw_price is None or isinstance(raw_price, bool):
        return f"Món '{dish_name}' thiếu thông tin giá hợp lệ"
    try:
        price_vnd = int(raw_price)
    except (TypeError, ValueError):
        return f"Món '{dish_name}' có giá không hợp lệ: {raw_price!r}"
    if price_vnd < 0:
        return f"Món '{dish_name}' có giá âm: {price_vnd}"

    budget = member.get("budget_vnd")
    if budget is not None:
        if isinstance(budget, bool):
            return f"Ngân sách của thành viên không hợp lệ: {budget!r}"
        try:
            budget_vnd = int(budget)
        except (TypeError, ValueError):
            return f"Ngân sách của thành viên không hợp lệ: {budget!r}"
        if budget_vnd < 0:
            return f"Ngân sách của thành viên không hợp lệ: {budget_vnd:,}đ"
        total_cost = price_vnd + ship_per_person
        if total_cost > budget_vnd:
            return (
                f"Món '{dish_name}' ({price_vnd:,}đ + {ship_per_person:,}đ ship = "
                f"{total_cost:,}đ) vượt ngân sách {budget_vnd:,}đ"
            )
    return None


@tool
def suggest_restaurants(members: Optional[List[Dict[str, Any]]] = None, max_results: int = 3, *,
                        require_exact_dishes: bool = False) -> List[Dict[str, Any]]:
    """Tên: suggest_restaurants — Lọc và gợi ý tối đa 3 quán phù hợp từ danh sách quán mẫu (Bước 3).
    Input: members (ràng buộc từng người), max_results (int, tối đa 3), require_exact_dishes (lọc theo món bắt buộc).
    Output: danh sách tối đa 3 quán phù hợp kèm shipping_fee_vnd, ship_per_person_vnd và số món hợp lệ cho từng người.
    Tác động ra ngoài: Không."""
    restaurants = _load_restaurants_data()
    members = members if isinstance(members, list) else []
    try:
        limit = min(max(1, int(max_results)), 3)
    except (TypeError, ValueError):
        limit = 3
    n_members = max(1, len(members))
    candidates = []
    preference_scores = {}

    for rest in restaurants:
        ship_fee = int(rest.get("shipping_fee_vnd", 0))
        ship_share = math.ceil(ship_fee / n_members)
        menu = [d for d in rest.get("menu", []) if d.get("in_stock", False)]

        if not members:
            candidates.append({
                "restaurant_id": rest["restaurant_id"],
                "name": rest["name"],
                "style": rest.get("style", ""),
                "shipping_fee_vnd": ship_fee,
                "ship_per_person_vnd": ship_share,
                "in_stock_count": len(menu),
                "feasible_for_all": True,
            })
            continue

        all_ok = True
        per_member_options = {}
        preference_score = 0
        for idx, m in enumerate(members):
            if not isinstance(m, dict):
                all_ok = False
                continue
            m_name = str(m.get("name") or f"Nguoi_{idx + 1}").strip() or f"Nguoi_{idx + 1}"
            ok_dishes = [dish for dish in menu if _dish_satisfies_member(dish, m, ship_share) is None]
            if require_exact_dishes and m.get("dish_required"):
                exact = _menu_match(ok_dishes, m.get("requested_dish") or m.get("preferred_dish"))
                ok_dishes = [exact] if exact else []
            per_member_options[m_name] = len(ok_dishes)
            if not ok_dishes:
                all_ok = False
            preference = _strip_accents(str(m.get("preferred_dish") or "").strip().lower())
            if preference and any(preference in _strip_accents(dish["ten_mon"].lower()) for dish in ok_dishes):
                preference_score += 1

        if all_ok:
            preference_scores[rest["restaurant_id"]] = preference_score
            candidates.append({
                "restaurant_id": rest["restaurant_id"],
                "name": rest["name"],
                "style": rest.get("style", ""),
                "shipping_fee_vnd": ship_fee,
                "ship_per_person_vnd": ship_share,
                "in_stock_count": len(menu),
                "feasible_for_all": True,
                "options_per_member": per_member_options,
            })

    candidates.sort(key=lambda candidate: preference_scores.get(candidate["restaurant_id"], 0), reverse=True)
    return candidates[:limit]


@tool
def get_restaurant_menu(restaurant_id: str, recent_dishes: Optional[List[str]] = None) -> Dict[str, Any]:
    """Tên: get_restaurant_menu — Lấy danh sách món còn hàng của 1 quán và đánh dấu món vừa ăn cần tránh (Bước 4).
    Input: restaurant_id (str, vd 'Q01'), recent_dishes (list tên món hoặc dish_id vừa ăn gần đây).
    Output: dict gồm thông tin quán, shipping_fee_vnd, danh sách menu còn hàng (kèm cờ is_recent) và món đã hết hàng.
    Tác động ra ngoài: Không."""
    restaurants = _load_restaurants_data()
    rest_key = str(restaurant_id or "").upper().strip()
    recent_norm = {str(x).lower().strip() for x in _as_list(recent_dishes) if str(x).strip()}
    target = next((r for r in restaurants if str(r.get("restaurant_id") or "").upper() == rest_key), None)
    if not target:
        return {"found": False, "error": f"Không tìm thấy quán '{restaurant_id}' trong dữ liệu mẫu."}

    available = []
    out_of_stock = []
    for dish in target.get("menu", []):
        dish_id = str(dish.get("dish_id") or "")
        ten_mon = str(dish.get("ten_mon") or "")
        is_recent = (
            dish_id.lower() in recent_norm
            or ten_mon.lower().strip() in recent_norm
        )
        entry = dict(dish)
        entry["is_recent"] = is_recent
        if dish.get("in_stock", False):
            available.append(entry)
        else:
            out_of_stock.append({"dish_id": dish_id, "ten_mon": ten_mon})

    return {
        "found": True,
        "restaurant_id": target["restaurant_id"],
        "name": target["name"],
        "shipping_fee_vnd": target["shipping_fee_vnd"],
        "available_menu": available,
        "out_of_stock": out_of_stock,
    }


@tool
def validate_cart(
    restaurant_id: str,
    selections: List[Dict[str, Any]],
    members: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Tên: validate_cart — Kiểm tra tất định giỏ món theo menu, tồn hàng, đủ suất, điều kiêng và ngân sách gồm ship (Bước 5 & 8).
    Input: restaurant_id (str), selections (list {'member_name', 'dish_id', 'is_blind_bag'}), members (list ràng buộc từng người).
    Output: dict {'ok': bool, 'ship_per_person_vnd': int, 'total_food_vnd': int, 'total_order_vnd': int, 'items': list, 'errors': list}.
    Tác động ra ngoài: Không."""
    restaurants = _load_restaurants_data()
    rest_key = str(restaurant_id or "").upper().strip()
    target = next((r for r in restaurants if str(r.get("restaurant_id") or "").upper() == rest_key), None)
    if not target:
        return {"ok": False, "errors": [f"Quán '{restaurant_id}' không tồn tại trong danh sách quán mẫu."]}

    if not isinstance(members, list) or not members:
        return {"ok": False, "errors": ["Thiếu danh sách thành viên để kiểm tra đủ suất."]}
    if not isinstance(selections, list):
        return {"ok": False, "errors": ["Danh sách món được chọn (selections) không hợp lệ."]}

    errors: List[str] = []
    if len(selections) != len(members):
        errors.append(f"Chưa đủ/đúng số suất: có {len(members)} người nhưng giỏ đang có {len(selections)} suất.")

    menu_by_id = {
        str(d["dish_id"]).upper().strip(): d
        for d in target.get("menu", [])
        if isinstance(d, dict) and d.get("dish_id")
    }
    menu_by_name = {
        str(d["ten_mon"]).lower().strip(): d
        for d in target.get("menu", [])
        if isinstance(d, dict) and d.get("ten_mon")
    }

    member_entries = []
    members_idx_by_name: Dict[str, List[int]] = {}
    for i, m in enumerate(members):
        if not isinstance(m, dict):
            errors.append(f"Thông tin thành viên tại vị trí {i + 1} không hợp lệ.")
            continue
        display_name = str(m.get("name") or f"Nguoi_{i + 1}").strip() or f"Nguoi_{i + 1}"
        norm_name = display_name.lower()
        member_entries.append((i, display_name, norm_name, m))
        members_idx_by_name.setdefault(norm_name, []).append(i)

    ship_fee = int(target.get("shipping_fee_vnd", 0))
    ship_share = math.ceil(ship_fee / max(1, len(members)))

    checked_items = []
    assigned_member_indices = set()
    total_food = 0

    for idx, sel in enumerate(selections):
        if not isinstance(sel, dict):
            errors.append(f"Suất thứ {idx + 1} không hợp lệ (thiếu cấu trúc dict).")
            continue

        raw_m_name = sel.get("member_name")
        has_explicit_name = bool(raw_m_name is not None and str(raw_m_name).strip())
        member_idx: Optional[int] = None
        member: Optional[Dict[str, Any]] = None
        m_name = str(raw_m_name).strip() if has_explicit_name else ""

        if has_explicit_name:
            cand_indices = members_idx_by_name.get(m_name.lower(), [])
            if not cand_indices:
                errors.append(f"Không tìm thấy thông tin ràng buộc cho thành viên '{m_name}'.")
                continue
            unassigned = [ci for ci in cand_indices if ci not in assigned_member_indices]
            if not unassigned:
                errors.append(f"[{m_name}] Thành viên '{m_name}' bị chọn trùng nhiều suất.")
                continue
            member_idx = unassigned[0]
            member = members[member_idx]
        else:
            if idx >= len(members) or not isinstance(members[idx], dict):
                errors.append(f"Suất thứ {idx + 1} thiếu 'member_name' và không khớp được thành viên.")
                continue
            if idx in assigned_member_indices:
                m_fallback = str(members[idx].get("name") or f"Nguoi_{idx + 1}")
                errors.append(f"[{m_fallback}] Thành viên '{m_fallback}' bị chọn trùng nhiều suất.")
                continue
            member_idx = idx
            member = members[idx]
            m_name = str(member.get("name") or f"Nguoi_{idx + 1}").strip() or f"Nguoi_{idx + 1}"

        assigned_member_indices.add(member_idx)

        dish_key = str(sel.get("dish_id") or "").strip()
        ten_mon_key = str(sel.get("ten_mon") or "").strip()
        if not dish_key and not ten_mon_key:
            errors.append(f"[{m_name}] Thiếu 'dish_id' hoặc 'ten_mon' trong suất được chọn.")
            continue

        dish = menu_by_id.get(dish_key.upper()) or menu_by_name.get(dish_key.lower())
        if not dish and ten_mon_key:
            dish = menu_by_name.get(ten_mon_key.lower())

        if not dish:
            errors.append(f"[{m_name}] Món '{dish_key or ten_mon_key}' không tồn tại trong menu quán {target['restaurant_id']}.")
            continue

        reason = _dish_satisfies_member(dish, member, ship_share)
        if reason:
            errors.append(f"[{m_name}] {reason}")
            continue

        price = int(dish["price_vnd"])
        total_food += price
        kitchen_notes = _dish_garnish_notes(dish, member)
        checked_items.append({
            "member_name": m_name,
            "dish_id": dish["dish_id"],
            "ten_mon": dish["ten_mon"],
            "price_vnd": price,
            "ship_share_vnd": ship_share,
            "total_member_vnd": price + ship_share,
            "is_blind_bag": bool(sel.get("is_blind_bag", False)),
            "kitchen_note": ", ".join(kitchen_notes),
        })

    for i, display_name, _, _ in member_entries:
        if i not in assigned_member_indices:
            errors.append(f"Thiếu suất cho thành viên '{display_name}'.")

    return {
        "ok": (
            len(errors) == 0
            and len(checked_items) == len(members)
            and len(assigned_member_indices) == len(members)
        ),
        "restaurant_id": target["restaurant_id"],
        "restaurant_name": target["name"],
        "shipping_fee_vnd": ship_fee,
        "ship_per_person_vnd": ship_share,
        "total_food_vnd": total_food,
        "total_order_vnd": total_food + ship_fee,
        "items": checked_items,
        "errors": errors,
    }


@tool
def save_order_history(order_id: str, restaurant_id: str, validated_cart: Dict[str, Any]) -> Dict[str, Any]:
    """Tên: save_order_history — Lưu lịch sử đơn đã kiểm hợp lệ vào SQLite cục bộ (Bước 8).
    Input: order_id (str), restaurant_id (str), validated_cart (dict kết quả đạt từ validate_cart).
    Output: dict trạng thái {'saved': bool, 'path': str, 'message': str}.
    Tác động ra ngoài: Chỉ ghi SQLite cục bộ; KHÔNG đặt đơn, KHÔNG gửi tin hay thanh toán thật."""
    from storage import finalize

    if not isinstance(validated_cart, dict) or not validated_cart.get("ok"):
        return {
            "saved": False,
            "path": "data/lunchie.sqlite3",
            "message": "Không thể lưu lịch sử vì giỏ chưa vượt qua bước kiểm tra validate_cart.",
        }
    record = finalize(str(order_id or "").strip(), validated_cart, [], save_profiles=False)

    return {
        "saved": True,
        "path": "data/lunchie.sqlite3",
        "message": f"Đã lưu lịch sử đơn {record['order_id']} (bản nháp cuối, chờ người đặt tự bấm đặt trên app).",
    }
