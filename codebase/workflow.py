"""Shared, model-assisted Lunchie workflow. Python remains authoritative for safety and totals."""
import json
import re
import unicodedata

from ai import ModelError, call_model
from tools import _dish_satisfies_member, _menu_match, _to_slug, get_restaurant_menu, suggest_restaurants, validate_cart

EXTRACT_SCHEMA = {"name": "lunch_request", "schema": {
    "type": "object", "properties": {
        "members": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "budget_vnd": {"type": ["integer", "null"]},
            "allergies": {"type": "array", "items": {"type": "string"}},
            "avoid_keywords": {"type": "array", "items": {"type": "string"}},
            "vegetarian": {"type": "boolean"}, "preferred_dish": {"type": "string"},
            "requested_dish": {"type": "string"}, "dish_required": {"type": "boolean"},
            "current_dish": {"type": "string"}, "blind_bag": {"type": "boolean"}},
            "required": ["name", "budget_vnd", "allergies", "avoid_keywords", "vegetarian",
                         "preferred_dish", "requested_dish", "dish_required", "current_dish", "blind_bag"],
            "additionalProperties": False}},
        "restaurant_id": {"type": ["string", "null"]},
        "intent": {"type": "string", "enum": ["plan", "swap", "refuse", "clarify"]},
        "swap_member": {"type": ["string", "null"]}, "swap_feedback": {"type": "string"},
        "avoid_dishes": {"type": "array", "items": {"type": "string"}},
        "missing_fields": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"}},
    "required": ["members", "restaurant_id", "intent", "swap_member", "swap_feedback",
                 "avoid_dishes", "missing_fields", "reason"], "additionalProperties": False}}
PICK_SCHEMA = {"name": "lunch_cart", "schema": {"type": "object", "properties": {
    "items": {"type": "array", "items": {"type": "object", "properties": {"member_name": {"type": "string"}, "dish_id": {"type": "string"}}, "required": ["member_name", "dish_id"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False}}


def _json_call(system, payload, schema):
    result = call_model(system, json.dumps(payload, ensure_ascii=False), schema=schema)
    try:
        value = json.loads(result["text"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ModelError("AI trả dữ liệu không hợp lệ. Hãy thử lại.") from exc
    if not isinstance(value, dict):
        raise ModelError("AI trả dữ liệu sai cấu trúc. Hãy thử lại.")
    return value


def extract_request(text, shared_budget=None):
    if type(shared_budget) is not int or shared_budget <= 0:
        shared_budget = _extract_budget(text)
    restaurants = suggest_restaurants(members=[], max_results=20)
    known = [{"restaurant_id": r["restaurant_id"], "name": r["name"]} for r in restaurants]
    parsed = _json_call(
        "Trích xuất yêu cầu đặt bữa trưa theo schema. intent=plan với yêu cầu lập giỏ, "
        "intent=refuse nếu bị yêu cầu làm ngoài phạm vi, bịa giá, hoặc bỏ qua an toàn. "
        "Chép nguyên tên người. Giữ ngân sách mới nhất và ràng buộc dị ứng/kiêng của đúng người. "
        "budget_vnd là nguyên hạn mức người dùng nêu đã gồm ship. Không tự tính hay trừ phí ship khỏi hạn mức. "
        "blind_bag chỉ bật cho người giao quyền chọn hoặc có nhãn Túi mù. "
        "preferred_dish có thể là loại món. requested_dish ghi nguyên văn mã hoặc tên món cụ thể "
        "được hỏi hoặc muốn chọn, kể cả nếu chưa biết món có trong menu. Để trống nếu chỉ nêu loại món, "
        "món đã ăn, món cũ hoặc món cần tránh. dish_required chỉ bật nếu người đó chỉ chấp nhận món đã nêu. "
        "Nếu yêu cầu thay một suất trong giỏ có sẵn, kể cả vì ngân sách đổi, đặt intent=swap. "
        "Điền current_dish của từng người theo giỏ hiện tại, swap_member là người cần đổi, "
        "swap_feedback ghi yêu cầu mới của người đó. Không coi món hiện tại là preferred_dish hoặc requested_dish. "
        "Các trường món hoặc phản hồi để trống nếu không được nêu. restaurant_id dùng mã quán đã cho.",
        {"message": str(text)[:12000], "shared_budget_vnd": shared_budget, "known_restaurants": known}, EXTRACT_SCHEMA)
    members = parsed.get("members")
    if not isinstance(members, list):
        members = []
    clean = []
    for member in members[:20]:
        if not isinstance(member, dict):
            continue
        name = str(member.get("name") or "").strip()
        budget = member.get("budget_vnd", shared_budget)
        if type(budget) is not int or budget <= 0:
            budget = shared_budget if type(shared_budget) is int and shared_budget > 0 else None
        clean.append({"name": name, "budget_vnd": budget,
                      "allergies": [str(x).strip() for x in member.get("allergies", []) if str(x).strip()],
                      "avoid_allergens": [],
                      "avoid_keywords": [str(x).strip() for x in member.get("avoid_keywords", []) if str(x).strip()],
                      "vegetarian": bool(member.get("vegetarian")),
                      "preferred_dish": str(member.get("preferred_dish") or "").strip(),
                      "requested_dish": _source_phrase(text, member.get("requested_dish")),
                      "dish_required": bool(member.get("dish_required")),
                      "current_dish": _source_phrase(text, member.get("current_dish")),
                      "blind_bag": bool(member.get("blind_bag"))})
    _augment_member_details(str(text), clean)
    names = [_norm(m["name"]) for m in clean]
    # Missing data is derived locally. Model-generated field names are not trusted as blockers.
    missing = []
    if not clean:
        missing.append("số người và tên")
    if any(not m["name"].strip() for m in clean) or len(set(names)) != len(names):
        missing.append("tên riêng cho từng người")
    if any(m["budget_vnd"] is None for m in clean):
        missing.append("ngân sách đã gồm phí ship cho từng người")
    parsed["members"] = clean
    parsed["missing_fields"] = list(dict.fromkeys(str(x) for x in missing))
    normalized_text = _norm(text)
    explicit_unsafe = (
        ("thanh toan" in normalized_text and any(term in normalized_text for term in ("ho", "giup", "thay toi")))
        or ("bam dat" in normalized_text and any(term in normalized_text for term in ("ho", "tu dong", "thay toi")))
        or ("bo qua" in normalized_text and any(term in normalized_text for term in ("di ung", "kieng", "an toan")))
        or any(term in normalized_text for term in ("sua gia", "giam gia", "ma giam"))
    )
    obvious_meal = any(term in normalized_text for term in ("com trua", "dat com", "dat bua trua", "mon an", "mon com"))
    if explicit_unsafe:
        parsed["intent"] = "refuse"
    elif obvious_meal and parsed.get("intent") == "refuse":
        parsed["intent"] = "plan"
    rid = parsed.get("restaurant_id")
    explicit_id = re.search(r"\b(Q\d{2,})\b", str(text), flags=re.I)
    rid = explicit_id.group(1) if explicit_id else rid
    parsed["restaurant_id"] = rid.upper() if isinstance(rid, str) and re.fullmatch(r"Q\d{2,}", rid, re.I) else None
    return parsed


def _norm(value):
    raw = unicodedata.normalize("NFD", str(value or "").lower().replace("đ", "d"))
    return "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")


def _has_phrase(text, phrase):
    return bool(phrase and re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text))


def _source_phrase(text, value):
    phrase = str(value or "").strip()
    return phrase if _has_phrase(_norm(text), _norm(phrase)) else ""


_MONEY = r"(\d+(?:[.,]\d{3})*)\s*(k|nghin|ngan|vnd|dong|d)\b"


def _money_value(match):
    value = int(re.sub(r"[.,]", "", match[1]))
    return value * 1000 if match[2] in ("k", "nghin", "ngan") else value


def _extract_budget(text):
    normalized = _norm(text).replace(".", "").replace(",", "")
    match = re.search(r"(?:ngan sach(?: chung| toi da)?|budget(?: chung)?|duoi|toi da)[^0-9]{0,40}(\d+)\s*(k|nghin|ngan|d|dong|vnd)?", normalized)
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2) or ""
    if unit in ("k", "nghin", "ngan"):
        value *= 1000
    elif value < 1000:
        return None
    return value if value > 0 else None


def _explicit_budget(clause):
    matches = re.finditer(
        r"(?:^\s*[:(]?\s*|\b(?:ngan sach(?:\s+(?:cung|toi da|xuong|con|la))*|"
        r"toi da|duoi|van|co)\s+)" + _MONEY,
        clause,
    )
    amounts = [_money_value(match) for match in matches]
    return amounts[-1] if amounts and amounts[-1] > 0 else None


def _dish_preference(value):
    normalized = re.sub(r"^(?:mon(?: an)?|an)\s+", "", _norm(value).strip())
    return re.sub(r"\s+(?:khong cay|it cay|khong ot)$", "", normalized)


def _augment_member_details(text, members):
    """Bind explicit phrases even when names occur earlier in a budget list."""
    positions = []
    for member in members:
        if member["name"]:
            pattern = r"(?<!\w)" + re.escape(member["name"]) + r"(?!\w)"
            positions.extend((match.start(), match.end(), member)
                             for match in re.finditer(pattern, text, flags=re.IGNORECASE))
    positions.sort(key=lambda item: (item[0], -item[1]))
    mentions = []
    for position in positions:
        if not mentions or position[0] >= mentions[-1][1]:
            mentions.append(position)
    scopes = {}
    for i, (_, name_end, member) in enumerate(mentions):
        end = mentions[i + 1][0] if i + 1 < len(mentions) else len(text)
        scopes.setdefault(id(member), []).append(_norm(text[name_end:end]))
    blind_cue = re.compile(r"\b(?:gi cung duoc|tui mu)\b")
    group_budget = re.search(
        r"\b(?:(?:ngan sach|budget)(?:\s+(?:chung|cung|toi da))*|toi da|muc chi)\s+"
        + _MONEY + r"\s*(?:/\s*nguoi|moi nguoi)\b",
        _norm(text),
    )
    group_budget = _money_value(group_budget) if group_budget else None
    explicit_blind = {
        key for key, clauses in scopes.items()
        if any(blind_cue.search(re.sub(r"\bkhong(?: phai| muon| chon| gan)?\s+tui mu\b", "", clause))
               for clause in clauses)
    }
    for member in members:
        clauses = scopes.get(id(member))
        if not clauses:
            continue
        clause = ". ".join(clauses)
        explicit_budget = next((amount for part in reversed(clauses)
                                if (amount := _explicit_budget(part)) is not None), None)
        if explicit_budget is not None or group_budget:
            member["budget_vnd"] = explicit_budget if explicit_budget is not None else group_budget
        if explicit_blind:
            member["blind_bag"] = id(member) in explicit_blind
        member["dish_required"] = bool(member["requested_dish"] and re.search(
            r"\bchi\s+(?:muon(?:\s+(?:an|goi|chon))?|an|goi|chon|nhan)\s+"
            + re.escape(_norm(member["requested_dish"]).split(" (", 1)[0]) + r"(?!\w)", clause))
        avoids = list(member.get("avoid_keywords", []))
        allergies = list(member.get("allergies", []))
        if "an chay" in clause and "khong an chay" not in clause:
            member["vegetarian"] = True
        if "khong cay" in clause or "khong an cay" in clause:
            avoids.append("cay")
        if "khong an thit heo" in clause or "khong an heo" in clause:
            avoids.append("thịt heo")
        if "khong an hai san" in clause or "di ung hai san" in clause:
            allergies.extend(["tôm", "cá", "mực", "nghêu", "sò", "cua"])
        if "di ung dau phong" in clause:
            allergies.append("đậu phộng")
        if re.search(r"\b(?:chi an|muon|can|chon)\s+mon man\b", clause):
            member["require_non_vegetarian"] = True
        member["avoid_keywords"] = list(dict.fromkeys(avoids))
        member["allergies"] = list(dict.fromkeys(allergies))
        recent = re.search(r"vua an\s+(.+?)(?:\s+(?:o don truoc|nen chon|nen tranh)|[,.;]|$)", clause)
        if recent:
            member["recent_dish_name"] = recent.group(1).strip()


def recommend_restaurants(members):
    restaurants = suggest_restaurants(members=members, max_results=3)
    # If no feasible venue, still surface up to three venues to let Python explain constraints.
    if not restaurants:
        restaurants = suggest_restaurants(members=[], max_results=3)
    return restaurants


def _requested_dishes(menu, member):
    explicit = member.get("requested_dish")
    reference = explicit or member.get("preferred_dish")
    available = _menu_match(menu["available_menu"], reference)
    sold_out = _menu_match(menu["out_of_stock"], reference)
    return explicit, available, sold_out


def _allergy_guidance(member):
    allergens = ", ".join(member["allergies"])
    return (f"Chưa đủ căn cứ từ menu mẫu để xác nhận món thay thế phù hợp với dị ứng ({allergens}) "
            "cho " + member["name"] + ". Hãy hỏi quán về nguyên liệu và nguy cơ tiếp xúc chéo trước khi đặt.")


def build_cart(restaurant_id, members, recent_by_member=None, avoid_dishes=None):
    menu = get_restaurant_menu(restaurant_id, recent_dishes=[])
    if not menu.get("found"):
        return {"ok": False, "errors": [menu.get("error", "Không tìm thấy quán.")], "menu": menu}
    recent_by_member = recent_by_member or {}
    avoid_dishes = avoid_dishes or []
    options = []
    replacement_options = []
    notices = []
    errors = []
    share = (menu["shipping_fee_vnd"] + len(members) - 1) // max(1, len(members))
    for member in members:
        eligible = [dish for dish in menu["available_menu"]
                    if _dish_satisfies_member(dish, member, share) is None]
        reference, requested, sold_out = _requested_dishes(menu, member)
        preference = _dish_preference(member.get("preferred_dish") or reference)
        matching_options = [dish for dish in eligible if _has_phrase(_norm(dish["ten_mon"]), preference)]
        issue = ""
        if sold_out:
            issue = f"{sold_out['ten_mon']} có trong menu {restaurant_id} nhưng đã hết hàng"
        elif requested:
            issue = _dish_satisfies_member(requested, member, share) or ""
            if member.get("allergies"):
                allergy_names = {_to_slug(a): a for a in member["allergies"]}
                known = [allergy_names[tag] for tag in requested.get("allergens", []) if tag in allergy_names]
                if known:
                    issue = f"{requested['ten_mon']} có {', '.join(known)} theo dữ liệu thành phần"
        elif reference and not matching_options:
            issue = f"{reference} không có trong menu {restaurant_id}"
        if issue:
            notices.append(f"{member['name']}: {issue.rstrip('.')}.")
        if member.get("dish_required") and (reference or requested or sold_out):
            eligible = [dish for dish in eligible if requested and dish["dish_id"] == requested["dish_id"]]
            if not eligible and issue and not member.get("allergies"):
                errors.append("Hãy xác nhận món khác hoặc ngân sách mới cho " + member["name"] + ".")
                continue
        if not eligible:
            if member.get("allergies"):
                errors.append(_allergy_guidance(member))
                continue
            within_diet = {**member, "budget_vnd": None}
            cheapest = min((dish for dish in menu["available_menu"]
                            if _dish_satisfies_member(dish, within_diet, share) is None),
                           key=lambda dish: dish["price_vnd"], default=None)
            if cheapest and member.get("budget_vnd") is not None and cheapest["price_vnd"] + share > member["budget_vnd"]:
                price = cheapest["price_vnd"]
                total = price + share
                over = total - member["budget_vnd"]
                errors.append(f"{member['name']} cần tối thiểu {total:,}đ cho {cheapest['ten_mon']} "
                              f"({price:,}đ + {share:,}đ phí ship mỗi người), vượt ngân sách {over:,}đ.")
            else:
                errors.append(f"Không có món trong menu {restaurant_id} thỏa ràng buộc của {member['name']}.")
            continue
        replacement_options.append(eligible)
        recent = recent_by_member.get(_norm(member["name"]))
        if recent and len(eligible) > 1:
            filtered = [dish for dish in eligible if _norm(dish["dish_id"]) != _norm(recent) and _norm(dish["ten_mon"]) != _norm(recent)]
            if filtered:
                eligible = filtered
        preferred = [dish for dish in eligible if _has_phrase(_norm(dish["ten_mon"]), preference)]
        if preferred:
            eligible = preferred
        options.append([{key: dish.get(key) for key in (
            "dish_id", "ten_mon", "price_vnd", "is_vegetarian", "is_spicy", "ingredient_status",
            "ingredients", "ingredient_tags", "allergens",
        )} for dish in eligible])
    if errors:
        return {"ok": False, "errors": notices + errors}
    picked = _json_call(
        "Chọn đúng một món cho mỗi thành viên từ danh sách options cùng vị trí. Chỉ dùng dish_id đã cho. Ưu tiên món khớp món muốn ăn; blind_bag cho phép lựa chọn bất kỳ; không đánh đổi ràng buộc. Trả đúng một phần tử mỗi người.",
        {"members": members, "options_per_member": options, "avoid_dishes": avoid_dishes}, PICK_SCHEMA)
    by_id = {d["dish_id"]: d for group in options for d in group}
    chosen = []
    used = set()
    for member, eligible in zip(members, options):
        entry = next((x for x in picked.get("items", []) if _norm(x.get("member_name")) == _norm(member["name"]) and x.get("member_name") not in used), None)
        dish = by_id.get(entry.get("dish_id")) if entry else None
        allowed = {d["dish_id"] for d in eligible}
        exact_choice = _menu_match(eligible, member.get("requested_dish") or member.get("preferred_dish"))
        if exact_choice:
            dish = exact_choice
        if not dish or dish["dish_id"] not in allowed:
            # Model is a recommender only. Safe deterministic fallback from the already filtered set.
            dish = eligible[0]
        chosen.append({"member_name": member["name"], "dish_id": dish["dish_id"], "is_blind_bag": bool(member.get("blind_bag"))})
        used.add(member["name"])
    checked = validate_cart(restaurant_id, chosen, members)
    if not checked.get("ok"):
        return {"ok": False, "errors": checked.get("errors", ["Giỏ chưa đạt kiểm tra."]), "cart": checked}
    return {"ok": True, "cart": checked, "options": options, "replacement_options": replacement_options, "notices": notices}


def recommend_swap(restaurant_id, members, selections, member_name, feedback, *, allowed_dish_ids=None):
    menu = get_restaurant_menu(restaurant_id)
    if not menu.get("found"):
        return {"ok": False, "errors": [menu.get("error", "Không tìm thấy quán.")]}
    name_key = _norm(member_name)
    member = next((m for m in members if _norm(m.get("name")) == name_key), None)
    idx = next((i for i, item in enumerate(selections) if _norm(item.get("member_name")) == name_key), None)
    if member is None or idx is None:
        return {"ok": False, "errors": ["Không xác định được thành viên cần đổi món."]}
    if not str(feedback or "").strip():
        return {"ok": False, "errors": ["Nhập lý do hoặc món muốn đổi sang."]}
    share = (menu["shipping_fee_vnd"] + len(members) - 1) // max(1, len(members))
    options = [d for d in menu["available_menu"] if d["dish_id"] != selections[idx]["dish_id"]
               and (allowed_dish_ids is None or d["dish_id"] in allowed_dish_ids)
               and _dish_satisfies_member(d, member, share) is None]
    if not options:
        return {"ok": False, "errors": [f"Không có món thay thế hợp lệ cho {member_name}."]}
    response = _json_call(
        "Chọn đúng một món thay thế từ options cho thành viên đã chỉ định. Ưu tiên phản hồi; mọi lựa chọn đã lọc an toàn và vừa ngân sách. Chỉ trả dish_id có trong options.",
        {"member_name": member_name, "feedback": str(feedback)[:1000], "current_dish_id": selections[idx]["dish_id"],
         "options": [{"dish_id": d["dish_id"], "ten_mon": d["ten_mon"], "price_vnd": d["price_vnd"]} for d in options]}, PICK_SCHEMA)
    allowed = {d["dish_id"] for d in options}
    entry = next((x for x in response.get("items", []) if _norm(x.get("member_name")) == _norm(member_name)), {})
    replacement = entry.get("dish_id") if entry.get("dish_id") in allowed else options[0]["dish_id"]
    changed = [dict(item) for item in selections]
    changed[idx]["dish_id"] = replacement
    cart = validate_cart(restaurant_id, changed, members)
    return {"ok": bool(cart.get("ok")), "cart": cart, "selections": changed,
            "errors": cart.get("errors", [])}


def _format_cart(cart, members, menu, *, explain=False, notices=()):
    lines = [*notices, f"Giỏ nháp tại {cart['restaurant_name']} (đã kiểm tra):"]
    by_name = {_norm(member["name"]): member for member in members}
    for item in cart["items"]:
        line = (f"- {item['member_name']}: {item['ten_mon']} · "
                f"{item['price_vnd']:,}đ + {item['ship_share_vnd']:,}đ ship")
        if item["is_blind_bag"]:
            line += " · Túi mù"
        if explain:
            member = by_name[_norm(item["member_name"])]
            dish = _menu_match(menu["available_menu"], item["dish_id"])
            wanted = member.get("requested_dish") or member.get("preferred_dish")
            if wanted and (_has_phrase(_norm(item["ten_mon"]), _norm(wanted))
                           or _norm(wanted) == _norm(item["dish_id"])):
                line += " — đúng món muốn ăn"
            elif member.get("vegetarian") and dish["is_vegetarian"]:
                line += " — phù hợp yêu cầu ăn chay"
            elif item["is_blind_bag"]:
                line += " — món còn hàng trong ngân sách"
            else:
                line += " — món còn hàng và đáp ứng các điều kiện đã kiểm tra"
        lines.append(line)
    lines.append(f"Tổng đơn: {cart['total_order_vnd']:,}đ. Đây là bản nháp, người đặt tự duyệt và đặt trên ứng dụng.")
    return "\n".join(lines)


def _update_existing_cart(extracted, restaurant_id, text):
    members = extracted["members"]
    swap_name = _source_phrase(text, extracted.get("swap_member"))
    if not restaurant_id or not swap_name or not any(_norm(m["name"]) == _norm(swap_name) for m in members):
        return "Mình cần tên người muốn đổi món và quán của giỏ hiện tại."
    menu = get_restaurant_menu(restaurant_id)
    if not menu["found"]:
        return menu["error"]
    selections = []
    before = None
    for member in members:
        current = _menu_match(menu["available_menu"] + menu["out_of_stock"], member["current_dish"])
        if current is None:
            return f"Mình cần tên hoặc mã món hiện tại của {member['name']} ở {restaurant_id} để giữ đúng các suất còn lại."
        selections.append({"member_name": member["name"], "dish_id": current["dish_id"],
                           "is_blind_bag": member["blind_bag"]})
        if _norm(member["name"]) == _norm(swap_name):
            before = current
    feedback = extracted.get("swap_feedback") or text
    result = recommend_swap(restaurant_id, members, selections, swap_name, feedback)
    if not result["ok"]:
        return "Giữ nguyên giỏ hiện tại. " + " ".join(result["errors"])
    after = next(item for item in result["cart"]["items"] if _norm(item["member_name"]) == _norm(swap_name))
    change = (f"Đã đổi suất của {after['member_name']} từ {before['ten_mon']} sang {after['ten_mon']}. "
              "Các suất còn lại giữ nguyên.")
    return _format_cart(result["cart"], members, menu, notices=[change])


def run_text(text):
    extracted = extract_request(text)
    intent = extracted.get("intent")
    if intent == "refuse":
        return "Lunchie chỉ hỗ trợ lập giỏ cơm trưa từ menu mẫu. Mình không thể đặt hàng, thanh toán, bịa giá hoặc bỏ qua điều kiện an toàn."
    normalized = _norm(text)
    if intent == "swap" and any(term in normalized for term in ("luot 2", "lan 2", "lan thu hai", "da doi mon 1 lan")):
        return "Mình không thể đổi món lần thứ hai cho cùng một người trong một giỏ. Giỏ hiện tại cần được giữ nguyên."
    if extracted["missing_fields"]:
        return "Mình cần bạn bổ sung: " + ", ".join(extracted["missing_fields"]) + "."
    members = extracted["members"]
    chosen = extracted.get("restaurant_id")
    if intent == "swap":
        return _update_existing_cart(extracted, chosen, text)
    restaurants = recommend_restaurants(members)
    if chosen and chosen not in {r["restaurant_id"] for r in restaurants}:
        menu = get_restaurant_menu(chosen)
        if not menu.get("found"):
            return f"Quán {chosen} không có trong menu mẫu. Mình chưa tạo giỏ."
        restaurants = [{"restaurant_id": chosen, "name": menu["name"], "shipping_fee_vnd": menu["shipping_fee_vnd"]}]
    elif not chosen:
        if not restaurants:
            return "Chưa tìm được quán phù hợp với ngân sách và điều kiện của cả nhóm. Hãy kiểm tra lại ràng buộc hoặc ngân sách."
        chosen = restaurants[0]["restaurant_id"]
    recent = {_norm(m["name"]): m.get("recent_dish_name") for m in members if m.get("recent_dish_name")}
    result = build_cart(chosen, members, recent_by_member=recent, avoid_dishes=extracted.get("avoid_dishes"))
    dish_venues = set(re.findall(r"\b(q\d{2,})-m\d+\b", normalized))
    if len(dish_venues) > 1 and re.search(r"\b(?:gop|ghep|chung mot don)\b", normalized):
        details = " ".join(result.get("errors") or result.get("notices") or [])
        return "Một giỏ chỉ dùng menu của một quán. " + (
            details or "Bạn muốn chọn quán nào để mình kiểm tra lại các suất?"
        )
    if not result["ok"]:
        return "Chưa thể tạo giỏ hợp lệ: " + " ".join(result["errors"])
    explain = bool(re.search(r"\b(?:ly do|vi sao|tai sao|giai thich)\b", normalized))
    notices = list(result["notices"])
    if notices:
        notices.append("Các suất thay thế dưới đây là gợi ý để người đặt duyệt.")
    menu = get_restaurant_menu(chosen) if explain else None
    return _format_cart(result["cart"], members, menu, explain=explain, notices=notices)
