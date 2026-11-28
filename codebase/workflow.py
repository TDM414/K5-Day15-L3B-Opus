"""Shared, model-assisted Lunchie workflow. Python remains authoritative for safety and totals."""
import json
import re
import unicodedata

from ai import ModelError, call_model
from tools import (
    _dish_has_garnish_in_recipe,
    _dish_satisfies_member,
    _load_restaurants_data,
    _menu_match,
    _to_slug,
    get_restaurant_menu,
    suggest_restaurants,
    validate_cart,
)
from tracing import note

POLICY_FLAGS = (
    "external_order_payment",
    "bypass_allergy",
    "price_or_voucher_tampering",
    "private_profile_access",
    "fake_live_verification",
)

DATA_GAPS = (
    "unverifiable_food_attribute",
    "live_status_or_eta",
)

_PREF_TAG_MAP = {
    "bo": {"thit_bo"},
    "thit bo": {"thit_bo"},
    "heo": {"thit_heo"},
    "thit heo": {"thit_heo"},
    "suon": {"thit_heo"},
    "ba roi": {"thit_heo"},
    "ga": {"gia_cam"},
    "thit ga": {"gia_cam"},
    "vit": {"gia_cam"},
    "ca": {"ca"},
    "hai san": {"hai_san"},
    "tom": {"hai_san"},
    "chay": {"chay"},
    "thit": {"thit_heo", "thit_bo"},
}

EXTRACT_SCHEMA = {
    "name": "lunch_request",
    "schema": {
        "type": "object",
        "properties": {
            "reason": {"type": "string"},
            "policy_flags": {
                "type": "array",
                "items": {"type": "string", "enum": list(POLICY_FLAGS)},
            },
            "data_gaps": {
                "type": "array",
                "items": {"type": "string", "enum": list(DATA_GAPS)},
            },
            "intent": {"type": "string", "enum": ["plan", "swap", "refuse", "clarify"]},
            "restaurant_id": {"type": ["string", "null"]},
            "members": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "budget_vnd": {"type": ["integer", "null"]},
                        "allergies": {"type": "array", "items": {"type": "string"}},
                        "avoid_keywords": {"type": "array", "items": {"type": "string"}},
                        "vegetarian": {"type": "boolean"},
                        "preferred_dish": {"type": "string"},
                        "requested_dish": {"type": "string"},
                        "dish_required": {"type": "boolean"},
                        "current_dish": {"type": "string"},
                        "blind_bag": {"type": "boolean"},
                    },
                    "required": [
                        "name",
                        "budget_vnd",
                        "allergies",
                        "avoid_keywords",
                        "vegetarian",
                        "preferred_dish",
                        "requested_dish",
                        "dish_required",
                        "current_dish",
                        "blind_bag",
                    ],
                    "additionalProperties": False,
                },
            },
            "swap_member": {"type": ["string", "null"]},
            "swap_feedback": {"type": "string"},
            "avoid_dishes": {"type": "array", "items": {"type": "string"}},
            "missing_fields": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "reason",
            "policy_flags",
            "data_gaps",
            "intent",
            "restaurant_id",
            "members",
            "swap_member",
            "swap_feedback",
            "avoid_dishes",
            "missing_fields",
        ],
        "additionalProperties": False,
    },
}

PICK_SCHEMA = {
    "name": "lunch_cart",
    "schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "member_name": {"type": "string"},
                        "dish_id": {"type": "string"},
                    },
                    "required": ["member_name", "dish_id"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    },
}

_EXTRACT_SYSTEM_PROMPT = (
    "Trích xuất yêu cầu đặt bữa trưa theo schema. Viết reason ngắn (<=15 từ) trước khi chốt policy_flags, data_gaps, intent.\n"
    "DỮ LIỆU MẪU: chỉ có tên món, giá mẫu, tồn kho mẫu, ship mẫu, is_vegetarian, is_spicy, allergens, ingredients tham chiếu. "
    "KHÔNG có: nhãn dinh dưỡng (ít dầu/calo/đường/muối, giàu đạm), giờ mở cửa/ETA/giá tồn kho live, hay quyền đọc hồ sơ riêng trong CSDL.\n"
    "policy_flags: external_order_payment (tự mở app/áp mã/đặt/thanh toán hộ); bypass_allergy (bỏ qua dị ứng/kiêng/an toàn); "
    "price_or_voucher_tampering (sửa giá/bịa voucher); private_profile_access (đọc/tiết lộ hồ sơ riêng từ CSDL); "
    "fake_live_verification (nói dối đã kiểm giá/tồn kho live hoặc đã đặt thành công).\n"
    "data_gaps: unverifiable_food_attribute (CHỈ dùng cho tiêu chí dinh dưỡng ngoài menu như ít dầu/calo; KHÔNG dùng cho dị ứng, thành phần nguyên liệu, ăn chay hay độ cay); "
    "live_status_or_eta (hỏi quán đang mở hay giờ giao ETA).\n"
    "intent: refuse nếu có policy_flags; clarify nếu có data_gaps hoặc thiếu dữ liệu cốt lõi; swap nếu đổi món trong giỏ sẵn (kể cả đổi ngân sách); "
    "plan cho lập giỏ nháp, kiểm tra khả thi hoặc kiểm tra món/dị ứng trên known_restaurants (Q01-Q06). "
    "Luôn trích đủ members, restaurant_id, budget_vnd (hạn mức gồm ship; để null nếu chỉ ghi giá món của giỏ sẵn), current_dish, requested_dish (nguyên văn mã/tên món được hỏi/chọn), preferred_dish (loại món), dish_required, blind_bag (chỉ khi 'ăn gì cũng được'/Túi mù). "
    "Khi swap: điền current_dish từng người, swap_member, swap_feedback."
)


def _json_call(system, payload, schema):
    result = call_model(system, json.dumps(payload, ensure_ascii=False), schema=schema)
    try:
        value = json.loads(result["text"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ModelError("AI trả dữ liệu không hợp lệ. Hãy thử lại.") from exc
    if not isinstance(value, dict):
        raise ModelError("AI trả dữ liệu sai cấu trúc. Hãy thử lại.")
    return value


def _list_all_restaurants():
    return [
        {
            "restaurant_id": r["restaurant_id"],
            "name": r["name"],
        }
        for r in _load_restaurants_data()
        if isinstance(r, dict) and r.get("restaurant_id")
    ]


def _all_menu_dishes():
    return [
        dish
        for r in _load_restaurants_data()
        if isinstance(r, dict)
        for dish in (r.get("menu") or [])
        if isinstance(dish, dict)
    ]


def _has_unhandled_attribute_pref(members, all_dishes):
    for member in members:
        pref = str(member.get("preferred_dish") or "").strip()
        if not pref:
            continue
        if _menu_match(all_dishes, pref):
            continue
        if any(_preference_matches(dish, pref) for dish in all_dishes):
            continue
        return True
    return False


def _get_menu_cached(restaurant_id, menu_cache=None):
    key = str(restaurant_id or "").upper().strip()
    if menu_cache is not None and key in menu_cache:
        return menu_cache[key]
    menu = get_restaurant_menu(restaurant_id, recent_dishes=[])
    if menu_cache is not None and key:
        menu_cache[key] = menu
    return menu


# Policy cues are matched on accent-stripped text. They describe *the AI acting* on an
# external system, not the user's own actions ("mình đặt hộ nhóm", "tự thanh toán").
_APP_NAMES = r"(?:app|ung dung|grab\w*|shopee\w*|baemin|befood|gojek)"
_EXTERNAL_ACTION_RE = re.compile(
    r"\bthanh toan\s+(?:giup|ho|thay)\b"
    r"|\bthanh toan\s+bang\s+(?:vi|the)\b"
    r"|\b(?:bam|nhan)\s+dat\b"
    r"|\bap\s+ma\b"
    r"|\bdat\s+va\s+thanh toan\b"
    r"|\b(?:tu|ban|hay|cu)\s+mo\s+" + _APP_NAMES + r"\b"
    r"|\bmo\s+" + _APP_NAMES + r"\s+(?:\S+\s+){0,4}(?:dat|thanh toan)\b"
)
_NEGATION_TAIL_RE = re.compile(r"\b(?:dung|khong|cam|chang|chua)(?:\s+(?:duoc|nen|co|bao gio))?\s*$")
_SAFETY_TARGET_RE = re.compile(r"\b(?:di ung|kieng|an toan)\b")
_PRICE_TAMPER_RE = re.compile(
    r"\b(?:sua|doi|ha|chinh)\s+gia(?:\s+mon)?\b"
    r"|\bsua\b[^.]{0,30}\bgia mon\b"
    r"|\bbia\b[^.]{0,20}\b(?:voucher|ma giam|khuyen mai|giam gia)\b"
)
_PROFILE_SOURCE_RE = re.compile(
    r"\b(?:ho so\s+(?:an uong|rieng|di ung|suc khoe)|ho so da luu|co so du lieu|database|du lieu da luu|lich su\s+(?:mon|an|dat))\b"
)
_PROFILE_VERB_RE = re.compile(r"\b(?:doc|xem|tiet lo|truy xuat|cho biet|tra)\b")
_SELF_MARKER_RE = re.compile(r"\b(?:cua minh|cua toi|minh da luu|toi da luu|cua em)\b")
_OTHER_PERSON_RE = re.compile(r"\b(?:dong nghiep|nguoi khac|ban ay|cua\s+(?!minh\b|toi\b|em\b|ban\b|quan\b|nhom\b)\w+)")
_FAKE_CLAIM_RE = re.compile(
    r"\bda\s+(?:xac minh|kiem tra)\s+(?:truc tiep|gia|ton kho|live)\b"
    r"|\b(?:don\s+)?da\s+(?:dat|chot)\s+(?:thanh cong|xong)\b"
    r"|\bdon\s+da\s+dat\b"
)
_SPEECH_ACT_RE = re.compile(r"\b(?:noi|bao|viet|xac nhan|khang dinh|thong bao|tra loi)\b")


def _has_unnegated(normalized_text, pattern, target_re, window=40):
    for match in re.finditer(pattern, normalized_text):
        if _NEGATION_TAIL_RE.search(normalized_text[max(0, match.start() - 15):match.start()]):
            continue
        if target_re.search(normalized_text[match.end():match.end() + window]):
            return True
    return False


def _detect_policy_flags(normalized_text, initial_flags):
    flags = [str(f) for f in (initial_flags or []) if f in POLICY_FLAGS]
    text = normalized_text
    if _EXTERNAL_ACTION_RE.search(text):
        flags.append("external_order_payment")
    if _has_unnegated(text, r"\b(?:bo qua|phot lo|mac ke|lo di)\b", _SAFETY_TARGET_RE):
        flags.append("bypass_allergy")
    if _PRICE_TAMPER_RE.search(text):
        flags.append("price_or_voucher_tampering")
    if (
        _PROFILE_SOURCE_RE.search(text)
        and _PROFILE_VERB_RE.search(text)
        and (_OTHER_PERSON_RE.search(text) or not _SELF_MARKER_RE.search(text))
    ):
        flags.append("private_profile_access")
    if _FAKE_CLAIM_RE.search(text) and _SPEECH_ACT_RE.search(text):
        flags.append("fake_live_verification")
    return list(dict.fromkeys(flags))


_NUTRITION_CUE_RE = re.compile(
    r"\b(?:it|giau)\s+(?:dau(?!\s+(?:phong|nanh|hu|phu|xanh|do|den|bap|que|ha lan))|mo|calo|duong|muoi|beo|dam|bot ngot)\b"
    r"|\bkhong\s+bot ngot\b"
    r"|\b(?:giam can|giam\s+\d+\s*kg|tang co|kiem dinh|calo)\b"
)


def _detect_data_gaps(normalized_text, initial_gaps):
    gaps = [str(g) for g in (initial_gaps or []) if g in DATA_GAPS]
    if re.search(
        r"\b(?:(?:dang|con)\s+mo(?:\s+cua)?|gio mo cua|giao truoc|giao kip|giao\s+(?:toi|den)\s+\S+(?:\s+\S+)?\s+truoc|eta)\b",
        normalized_text,
    ):
        gaps.append("live_status_or_eta")
    if _NUTRITION_CUE_RE.search(normalized_text):
        gaps.append("unverifiable_food_attribute")
    return list(dict.fromkeys(gaps))


_CONSTRAINT_ONLY_PHRASES = {
    "an gi cung duoc",
    "gi cung duoc",
    "tui mu",
    "khong an cay",
    "khong cay",
    "an chay",
    "mon chay",
    "mon man",
}

_AVOID_CANONICAL = {
    "hanh": "hành",
    "hanh la": "hành lá",
    "hanh phi": "hành phi",
    "hanh tay": "hành tây",
    "hanh tim": "hành tím",
    "ngo": "ngò",
    "ngo ri": "ngò rí",
    "rau mui": "rau mùi",
    "rau ram": "rau răm",
    "do chua": "đồ chua",
    "dua leo": "dưa leo",
    "ot": "ớt",
    "ot lat": "ớt lát",
    "tieu": "tiêu",
    "ga": "gà",
    "bo": "bò",
    "trung": "trứng",
    "ca": "cá",
}


def _split_dish_and_exclusions(raw_value):
    cleaned = str(raw_value or "").strip()
    if not cleaned:
        return "", []
    if _norm(cleaned) in _CONSTRAINT_ONLY_PHRASES:
        return "", []
    match = re.match(
        r"^(.+?)\s+kh[ôo]ng(?:\s+(?:[ăa]n|b[ỏo]|cho|d[ùu]ng))?\s+(.+)$",
        cleaned,
        flags=re.I,
    )
    if not match:
        return cleaned, []
    base = match.group(1).strip(" ,.;:-")
    raw_tail = match.group(2).strip()
    parts = re.split(r"\s*(?:,|;|/|\bv[àa]\b|\bv[ớơ]i\b|\bkh[ôo]ng(?:\s+(?:[ăa]n|b[ỏo]|cho|d[ùu]ng))?\b)\s*", raw_tail, flags=re.I)
    exclusions = [p.strip(" ,.;:-") for p in parts if p and p.strip(" ,.;:-")]
    if _norm(base) in _CONSTRAINT_ONLY_PHRASES:
        base = ""
    return base, exclusions


def extract_request(text, shared_budget=None):
    if type(shared_budget) is not int or shared_budget <= 0:
        shared_budget = _extract_budget(text)
    known = _list_all_restaurants()
    parsed = _json_call(
        _EXTRACT_SYSTEM_PROMPT,
        {"message": str(text)[:12000], "shared_budget_vnd": shared_budget, "known_restaurants": known},
        EXTRACT_SCHEMA,
    )
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
        pref_base, pref_excl = _split_dish_and_exclusions(member.get("preferred_dish"))
        req_raw, req_excl = _split_dish_and_exclusions(member.get("requested_dish"))
        req_base = _source_phrase(text, req_raw)
        avoids = [str(x).strip() for x in member.get("avoid_keywords", []) if str(x).strip()]
        avoids.extend(pref_excl)
        avoids.extend(req_excl)
        clean.append(
            {
                "name": name,
                "budget_vnd": budget,
                "allergies": [str(x).strip() for x in member.get("allergies", []) if str(x).strip()],
                "avoid_allergens": [],
                "avoid_keywords": list(dict.fromkeys(avoids)),
                "vegetarian": bool(member.get("vegetarian")),
                "preferred_dish": pref_base,
                "requested_dish": req_base,
                "dish_required": bool(member.get("dish_required")),
                "current_dish": _source_phrase(text, member.get("current_dish")),
                "blind_bag": bool(member.get("blind_bag")),
            }
        )
    _augment_member_details(str(text), clean)
    if len(clean) == 1 and not clean[0]["name"].strip():
        clean[0]["name"] = "Người đặt"
    names = [_norm(m["name"]) for m in clean]
    # Missing data is derived locally. Model-generated field names are not trusted as blockers.
    missing = []
    if not clean:
        missing.append("số người và tên")
    if len(clean) > 1 and (any(not m["name"].strip() for m in clean) or len(set(names)) != len(names)):
        missing.append("tên riêng cho từng người")
    if any(m["budget_vnd"] is None for m in clean):
        missing.append("ngân sách đã gồm phí ship cho từng người")
    parsed["members"] = clean
    parsed["missing_fields"] = list(dict.fromkeys(str(x) for x in missing))

    normalized_text = _norm(text)
    policy_flags = _detect_policy_flags(normalized_text, parsed.get("policy_flags"))
    data_gaps = _detect_data_gaps(normalized_text, parsed.get("data_gaps"))
    if "unverifiable_food_attribute" in data_gaps:
        # Keep a model-raised gap only when the text has a nutrition cue or an unmatched attribute preference.
        has_nutrition_cue = bool(_NUTRITION_CUE_RE.search(normalized_text))
        if clean and not has_nutrition_cue and not _has_unhandled_attribute_pref(clean, _all_menu_dishes()):
            data_gaps = [g for g in data_gaps if g != "unverifiable_food_attribute"]
    parsed["policy_flags"] = policy_flags
    parsed["data_gaps"] = data_gaps

    rid = parsed.get("restaurant_id")
    explicit_id = re.search(r"\b(Q\d{2,})\b", str(text), flags=re.I)
    rid = explicit_id.group(1) if explicit_id else rid
    parsed["restaurant_id"] = rid.upper() if isinstance(rid, str) and re.fullmatch(r"Q\d{2,}", rid, re.I) else None

    if policy_flags:
        parsed["intent"] = "refuse"
    elif data_gaps:
        parsed["intent"] = "clarify"
    elif parsed.get("intent") in ("refuse", "clarify") and clean and not missing:
        # Prevent false refusal/clarify when a valid venue/meal request has zero policy violations or data gaps.
        known_ids = {r["restaurant_id"] for r in known}
        meal_cue = any(
            term in normalized_text
            for term in ("com trua", "dat com", "dat bua trua", "dat nhap", "gio nhap", "len gio", "mon an", "mon com")
        )
        if meal_cue or parsed["restaurant_id"] in known_ids:
            parsed["intent"] = "plan"
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
    match = re.search(
        r"(?:ngan sach(?: chung| toi da)?|budget(?: chung)?|duoi|toi da)[^0-9]{0,40}(\d+)\s*(k|nghin|ngan|d|dong|vnd)?",
        normalized,
    )
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
    normalized = re.sub(r"^(?:mon(?:\s+an)?|com|an)\s+", "", _norm(value).strip())
    return re.sub(r"\s+(?:khong cay|it cay|khong ot)$", "", normalized)


def _preference_matches(dish, raw_pref):
    pref = _dish_preference(raw_pref)
    if not pref:
        return False
    dish_name_norm = _norm(dish.get("ten_mon", ""))
    if _has_phrase(dish_name_norm, pref):
        return True
    parts = [
        _dish_preference(part)
        for part in re.split(r"\s*(?:/|,|\bhoac\b|\bhay\b)\s*", pref)
        if _dish_preference(part)
    ]
    if not parts:
        parts = [pref]
    dish_tags = {_to_slug(tag) for tag in (dish.get("ingredient_tags") or []) if _to_slug(tag)}
    if dish.get("is_vegetarian"):
        dish_tags.add("chay")
    for token in parts:
        if _has_phrase(dish_name_norm, token):
            return True
        mapped_tags = _PREF_TAG_MAP.get(token)
        if mapped_tags and (mapped_tags & dish_tags):
            return True
    return False


_NAME_JOINER = re.compile(r"(?:\s|,|&|\bva\b|\bvoi\b)*")
_BLIND_NEGATION = re.compile(r"\bkhong(?: phai| muon| chon| gan| lay)?\s+tui mu\b")
_ALLERGY_STOP_WORDS = {
    "chi", "muon", "thich", "an", "khong", "nen", "can", "chon", "nhung", "ngan", "budget", "gom",
    "lay", "goi", "nguoi", "dat", "o", "tai", "neu", "thi", "la", "duoc", "nhe", "nha", "cho", "gi", "nao",
}


def _local_allergy_terms(raw_text):
    """Trích cục bộ 'dị ứng <X>' (tách theo và/,/với/hoặc); bỏ qua 'không dị ứng'."""
    found = []
    for match in re.finditer(
        r"(?<!không )(?<!khong )(?:dị ứng|di ung)(?:\s+(?:với|voi))?\s+([^.;\n]+)", str(raw_text or ""), flags=re.I
    ):
        for token in re.split(r"\s*(?:,|/|\bvà\b|\bva\b|\bvới\b|\bvoi\b|\bhoặc\b|\bhoac\b)\s*", match.group(1), flags=re.I):
            words = token.strip(" '\"()").split()
            kept = []
            norm_words = [_norm(word) for word in words]
            for idx, (word, norm_word) in enumerate(zip(words, norm_words)):
                next_word = norm_words[idx + 1] if idx + 1 < len(norm_words) else ""
                if (
                    norm_word in _ALLERGY_STOP_WORDS
                    or re.search(r"\d", norm_word)
                    or (norm_word == "toi" and next_word == "da")
                ):
                    break
                kept.append(word)
            truncated = len(kept) < len(words)
            if kept and len(kept) <= 3:
                found.append(" ".join(kept).strip(" ,"))
            if truncated or not kept or len(kept) > 3:
                break
    return list(dict.fromkeys(term for term in found if term))


def _apply_local_allergies(member, raw_text):
    allergies = list(member.get("allergies", []))
    allergies.extend(_local_allergy_terms(raw_text))
    allergies = list(dict.fromkeys(allergies))
    slugs = {_to_slug(a) for a in allergies if _to_slug(a)}
    member["allergies"] = allergies
    member["avoid_keywords"] = [
        term for term in member.get("avoid_keywords", [])
        if _to_slug(term) not in slugs
        and not any(_to_slug(term).startswith(s + "_") or s.startswith(_to_slug(term) + "_") for s in slugs)
    ]


def _augment_member_details(text, members):
    """Bind explicit phrases even when names occur earlier in a budget list."""
    positions = []
    for member in members:
        if member["name"]:
            pattern = r"(?<!\w)" + re.escape(member["name"]) + r"(?!\w)"
            positions.extend(
                (match.start(), match.end(), member)
                for match in re.finditer(pattern, text, flags=re.IGNORECASE)
            )
    positions.sort(key=lambda item: (item[0], -item[1]))
    mentions = []
    for position in positions:
        if not mentions or position[0] >= mentions[-1][1]:
            mentions.append(position)
    segments = []
    for i, (_, name_end, member) in enumerate(mentions):
        end = mentions[i + 1][0] if i + 1 < len(mentions) else len(text)
        segments.append([member, text[name_end:end]])
    # Tên nối nhau chỉ bằng ",", "và", "với" dùng chung vị ngữ phía sau (vd "Bình, Chi và Dũng ăn chay").
    for i in range(len(segments) - 2, -1, -1):
        if segments[i + 1][0] is not segments[i][0] and _NAME_JOINER.fullmatch(_norm(segments[i][1])):
            segments[i][1] = segments[i + 1][1]
    scopes = {}
    raw_scopes = {}
    for member, raw_segment in segments:
        scopes.setdefault(id(member), []).append(_norm(raw_segment))
        raw_scopes.setdefault(id(member), []).append(raw_segment)
    blind_cue = re.compile(r"\b(?:gi cung duoc|tui mu)\b")
    group_budget = re.search(
        r"\b(?:(?:ngan sach|budget)(?:\s+(?:chung|cung|toi da))*|toi da|muc chi)\s+"
        + _MONEY + r"\s*(?:/\s*nguoi|moi nguoi)\b",
        _norm(text),
    )
    group_budget = _money_value(group_budget) if group_budget else None
    explicit_blind = {
        key
        for key, clauses in scopes.items()
        if any(
            blind_cue.search(re.sub(r"\bkhong(?: phai| muon| chon| gan)?\s+tui mu\b", "", clause))
            for clause in clauses
        )
    }
    for member in members:
        clauses = scopes.get(id(member))
        if not clauses:
            if len(members) == 1:
                _apply_local_allergies(member, text)
            continue
        clause = ". ".join(clauses)
        explicit_budget = next(
            (amount for part in reversed(clauses) if (amount := _explicit_budget(part)) is not None),
            None,
        )
        if explicit_budget is not None or group_budget:
            member["budget_vnd"] = explicit_budget if explicit_budget is not None else group_budget
        if id(member) in explicit_blind:
            member["blind_bag"] = True
        elif _BLIND_NEGATION.search(clause):
            member["blind_bag"] = False
        elif explicit_blind and (
            member.get("requested_dish") or member.get("preferred_dish") or member.get("current_dish")
        ):
            # Người đã nêu món cụ thể không phải túi mù khi câu có chỉ rõ người khác là túi mù.
            member["blind_bag"] = False
        member["dish_required"] = bool(
            member["requested_dish"]
            and re.search(
                r"\bchi\s+(?:muon(?:\s+(?:an|goi|chon))?|an|goi|chon|nhan)\s+"
                + re.escape(_norm(member["requested_dish"]).split(" (", 1)[0])
                + r"(?!\w)",
                clause,
            )
        )
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
        for m_avoid in re.finditer(
            r"\bkhong\s+(?:(?:an|bo|cho|dung)\s+)?(hanh(?:\s+(?:la|phi|tay|tim))?|ngo(?:\s+ri)?|rau\s+(?:mui|ram)|do\s+chua|dua\s+leo|ot(?:\s+lat)?|tieu|ga|bo|trung|ca)\b",
            clause,
        ):
            token = re.sub(r"\s+", " ", m_avoid.group(1).strip())
            canonical = _AVOID_CANONICAL.get(token, token)
            if _to_slug(canonical) not in {_to_slug(a) for a in allergies}:
                avoids.append(canonical)
        if re.search(r"\b(?:chi an|muon|can|chon)\s+mon man\b", clause):
            member["require_non_vegetarian"] = True
        member["avoid_keywords"] = list(dict.fromkeys(avoids))
        member["allergies"] = list(dict.fromkeys(allergies))
        _apply_local_allergies(member, ". ".join(raw_scopes.get(id(member), [])))
        recent = re.search(r"vua an\s+(.+?)(?:\s+(?:o don truoc|nen chon|nen tranh)|[,.;]|$)", clause)
        if recent:
            member["recent_dish_name"] = recent.group(1).strip()


def recommend_restaurants(members):
    restaurants = suggest_restaurants(members=members, max_results=3)
    # Fallback list is unfiltered: callers that must know feasibility (run_text) call suggest_restaurants directly.
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
    return (
        f"Chưa đủ căn cứ từ menu mẫu để xác nhận món thay thế phù hợp với dị ứng ({allergens}) "
        "cho " + member["name"] + ". Hãy hỏi quán về nguyên liệu và nguy cơ tiếp xúc chéo trước khi đặt."
    )


def _compact_dish_entry(dish):
    return {
        "dish_id": dish.get("dish_id"),
        "ten_mon": dish.get("ten_mon"),
        "price_vnd": dish.get("price_vnd"),
        "dish_category": dish.get("dish_category"),
        "is_vegetarian": bool(dish.get("is_vegetarian")),
        "is_spicy": dish.get("is_spicy"),
        "ingredient_tags": list(dish.get("ingredient_tags") or []),
    }


def build_cart(restaurant_id, members, recent_by_member=None, avoid_dishes=None, menu_cache=None):
    menu = _get_menu_cached(restaurant_id, menu_cache)
    if not menu.get("found"):
        return {"ok": False, "errors": [menu.get("error", "Không tìm thấy quán.")], "menu": menu}
    recent_by_member = recent_by_member or {}
    avoid_dishes = avoid_dishes or []
    candidate_lists = []
    replacement_options = []
    notices = []
    errors = []
    share = (menu["shipping_fee_vnd"] + len(members) - 1) // max(1, len(members))
    for member in members:
        eligible = [
            dish for dish in menu["available_menu"]
            if _dish_satisfies_member(dish, member, share) is None
        ]
        reference, requested, sold_out = _requested_dishes(menu, member)
        pref_ref = reference or member.get("preferred_dish") or ""
        matching_options = [dish for dish in eligible if _preference_matches(dish, pref_ref)]
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
        elif pref_ref and not matching_options:
            conflicting = next(
                (kw for kw in member.get("avoid_keywords", []) if _has_phrase(_norm(pref_ref), _norm(kw))),
                None,
            )
            if conflicting:
                issue = (
                    f"Yêu cầu '{pref_ref}' mâu thuẫn với điều kiện tránh thành phần chính "
                    f"'{conflicting}', không thể ghi chú bỏ riêng"
                )
            else:
                issue = f"{pref_ref} không có trong menu {restaurant_id}"
        if issue:
            notices.append(f"{member['name']}: {issue.rstrip('.')}.")
        if member.get("dish_required") and (reference or requested or sold_out):
            eligible = [dish for dish in eligible if requested and dish["dish_id"] == requested["dish_id"]]
            if not eligible and issue and not member.get("allergies"):
                errors.append("Hãy xác nhận món khác hoặc ngân sách mới cho " + member["name"] + ".")
                continue
        if not eligible:
            if member.get("vegetarian") and member.get("require_non_vegetarian"):
                errors.append(
                    f"Yêu cầu của {member['name']} tự mâu thuẫn giữa ăn chay và chỉ ăn món mặn."
                )
                continue
            if member.get("allergies"):
                errors.append(_allergy_guidance(member))
                continue
            within_diet = {**member, "budget_vnd": None}
            cheapest = min(
                (dish for dish in menu["available_menu"] if _dish_satisfies_member(dish, within_diet, share) is None),
                key=lambda dish: dish["price_vnd"],
                default=None,
            )
            if cheapest and member.get("budget_vnd") is not None and cheapest["price_vnd"] + share > member["budget_vnd"]:
                price = cheapest["price_vnd"]
                total = price + share
                over = total - member["budget_vnd"]
                errors.append(
                    f"{member['name']} cần tối thiểu {total:,}đ cho {cheapest['ten_mon']} "
                    f"({price:,}đ + {share:,}đ phí ship mỗi người), vượt ngân sách {over:,}đ."
                )
            else:
                errors.append(f"Không có món trong menu {restaurant_id} thỏa ràng buộc của {member['name']}.")
            continue
        replacement_options.append(eligible)
        recent = recent_by_member.get(_norm(member["name"]))
        if recent and len(eligible) > 1:
            filtered = [
                dish for dish in eligible
                if _norm(dish["dish_id"]) != _norm(recent) and _norm(dish["ten_mon"]) != _norm(recent)
            ]
            if filtered:
                eligible = filtered
        pref_source = member.get("requested_dish") or member.get("preferred_dish")
        preferred = [dish for dish in eligible if _preference_matches(dish, pref_source)]
        if preferred:
            eligible = preferred
        exact_choice = _menu_match(eligible, pref_source)
        if exact_choice:
            eligible = [exact_choice]
        elif len(eligible) > 1 and member.get("avoid_keywords"):
            naturally_free = [dish for dish in eligible if not _dish_has_garnish_in_recipe(dish, member)]
            if naturally_free:
                eligible = naturally_free
        candidate_lists.append(eligible)
    if errors:
        return {"ok": False, "errors": notices + errors}

    catalog_by_id = {}
    for group in candidate_lists:
        for dish in group:
            did = dish["dish_id"]
            if did not in catalog_by_id:
                catalog_by_id[did] = _compact_dish_entry(dish)
    options = [[_compact_dish_entry(d) for d in group] for group in candidate_lists]

    if all(len(group) == 1 for group in candidate_lists):
        note("fast_path: deterministic single-candidate selection")
        picked = {"items": []}
    else:
        compact_payload = {
            "menu_catalog": list(catalog_by_id.values()),
            "members": [
                {
                    "name": member["name"],
                    "preferred_dish": member.get("preferred_dish") or "",
                    "blind_bag": bool(member.get("blind_bag")),
                    "eligible_dish_ids": [d["dish_id"] for d in group],
                }
                for member, group in zip(members, candidate_lists)
            ],
            "avoid_dishes": avoid_dishes,
        }
        picked = _json_call(
            "Chọn đúng một dish_id trong eligible_dish_ids cho mỗi thành viên dựa trên menu_catalog. "
            "Ưu tiên món khớp preferred_dish; tránh lặp trùng món không cần thiết cho người blind_bag hoặc món thay thế khi còn lựa chọn khác.",
            compact_payload,
            PICK_SCHEMA,
        )

    chosen = []
    used_members = set()
    used_dish_ids = set()
    for member, eligible in zip(members, candidate_lists):
        entry = next(
            (
                x for x in picked.get("items", [])
                if _norm(x.get("member_name")) == _norm(member["name"]) and x.get("member_name") not in used_members
            ),
            None,
        )
        by_id = {d["dish_id"]: d for d in eligible}
        dish = by_id.get(entry.get("dish_id")) if entry else None
        is_flexible = bool(member.get("blind_bag")) or (
            not member.get("requested_dish") and not member.get("preferred_dish")
        )
        if not dish:
            dish = next((d for d in eligible if d["dish_id"] not in used_dish_ids), eligible[0])
        elif is_flexible and dish["dish_id"] in used_dish_ids and len(eligible) > 1:
            alt = next((d for d in eligible if d["dish_id"] not in used_dish_ids), None)
            if alt:
                note(f"diversity_adjust: {member['name']} {dish['dish_id']}->{alt['dish_id']}")
                dish = alt
        chosen.append(
            {
                "member_name": member["name"],
                "dish_id": dish["dish_id"],
                "is_blind_bag": bool(member.get("blind_bag")),
            }
        )
        used_members.add(member["name"])
        used_dish_ids.add(dish["dish_id"])

    checked = validate_cart(restaurant_id, chosen, members)
    if not checked.get("ok"):
        return {"ok": False, "errors": checked.get("errors", ["Giỏ chưa đạt kiểm tra."]), "cart": checked}
    return {
        "ok": True,
        "cart": checked,
        "options": options,
        "replacement_options": replacement_options,
        "notices": notices,
    }


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
    options = [
        d for d in menu["available_menu"]
        if d["dish_id"] != selections[idx]["dish_id"]
        and (allowed_dish_ids is None or d["dish_id"] in allowed_dish_ids)
        and _dish_satisfies_member(d, member, share) is None
    ]
    if not options:
        return {"ok": False, "errors": [f"Không có món thay thế hợp lệ cho {member_name}."]}
    response = _json_call(
        "Chọn đúng một món thay thế từ options cho thành viên đã chỉ định. Ưu tiên phản hồi; mọi lựa chọn đã lọc an toàn và vừa ngân sách. Chỉ trả dish_id có trong options.",
        {
            "member_name": member_name,
            "feedback": str(feedback)[:1000],
            "current_dish_id": selections[idx]["dish_id"],
            "options": [
                {"dish_id": d["dish_id"], "ten_mon": d["ten_mon"], "price_vnd": d["price_vnd"]}
                for d in options
            ],
        },
        PICK_SCHEMA,
    )
    allowed = {d["dish_id"] for d in options}
    entry = next((x for x in response.get("items", []) if _norm(x.get("member_name")) == _norm(member_name)), {})
    replacement = entry.get("dish_id") if entry.get("dish_id") in allowed else options[0]["dish_id"]
    changed = [dict(item) for item in selections]
    changed[idx]["dish_id"] = replacement
    cart = validate_cart(restaurant_id, changed, members)
    return {"ok": bool(cart.get("ok")), "cart": cart, "selections": changed, "errors": cart.get("errors", [])}


def _format_cart(cart, members, menu, *, explain=False, notices=()):
    lines = [*notices, f"Giỏ nháp tại {cart['restaurant_name']} (đã kiểm tra):"]
    by_name = {_norm(member["name"]): member for member in members}
    for item in cart["items"]:
        line = (
            f"- {item['member_name']}: {item['ten_mon']} · "
            f"{item['price_vnd']:,}đ + {item['ship_share_vnd']:,}đ ship"
        )
        if item.get("kitchen_note"):
            line += f" · Ghi chú quán: {item['kitchen_note']}"
        if item["is_blind_bag"]:
            line += " · Túi mù"
        if explain and menu:
            member = by_name[_norm(item["member_name"])]
            dish = _menu_match(menu["available_menu"], item["dish_id"])
            wanted = member.get("requested_dish") or member.get("preferred_dish")
            if wanted and (
                _preference_matches(dish or item, wanted)
                or _norm(wanted) == _norm(item["dish_id"])
            ):
                line += " — đúng món muốn ăn"
            elif member.get("vegetarian") and dish and dish["is_vegetarian"]:
                line += " — phù hợp yêu cầu ăn chay"
            elif item["is_blind_bag"]:
                line += " — món còn hàng trong ngân sách"
            else:
                line += " — món còn hàng và đáp ứng các điều kiện đã kiểm tra"
        lines.append(line)
    lines.append(f"Tổng đơn: {cart['total_order_vnd']:,}đ. Đây là bản nháp, người đặt tự duyệt và đặt trên ứng dụng.")
    return "\n".join(lines)


def _validate_existing_draft(restaurant_id, members, menu_cache, text=""):
    if not restaurant_id or not members:
        return None
    menu = _get_menu_cached(restaurant_id, menu_cache)
    if not menu.get("found"):
        return None
    has_budget_cue = bool(re.search(r"\b(?:ngan sach|budget|toi da|duoi|muc chi)\b", _norm(text)))
    selections = []
    draft_members = []
    for member in members:
        dish_ref = member.get("current_dish") or member.get("requested_dish") or member.get("preferred_dish")
        dish = _menu_match(menu["available_menu"], dish_ref)
        if not dish:
            return None
        selections.append(
            {
                "member_name": member["name"],
                "dish_id": dish["dish_id"],
                "is_blind_bag": bool(member.get("blind_bag")),
            }
        )
        member_copy = dict(member)
        if not has_budget_cue or member_copy.get("budget_vnd") == dish.get("price_vnd"):
            member_copy["budget_vnd"] = None
        draft_members.append(member_copy)
    checked = validate_cart(restaurant_id, selections, draft_members)
    if not checked.get("ok"):
        return None
    return _format_cart(checked, draft_members, menu)


def _format_policy_response(extracted, menu_cache, text=""):
    flags = extracted.get("policy_flags") or []
    parts = []
    if "external_order_payment" in flags:
        parts.append(
            "Mình không thể tự mở ứng dụng, áp mã, đặt hàng hay thanh toán thay bạn. "
            "Lunchie chỉ lập bản nháp để người đặt tự kiểm tra và thao tác trên ứng dụng."
        )
        draft_text = _validate_existing_draft(
            extracted.get("restaurant_id"), extracted.get("members"), menu_cache, text=text
        )
        if draft_text:
            parts.append(draft_text)
    if "bypass_allergy" in flags:
        parts.append(
            "Mình không thể bỏ qua điều kiện dị ứng hay quy tắc an toàn thực phẩm, "
            "và sẽ không xếp món chứa nguyên liệu gây dị ứng vào giỏ."
        )
    if "price_or_voucher_tampering" in flags:
        parts.append(
            "Mình không thể sửa giá món, tạo giá giả hoặc bịa mã giảm giá/voucher; "
            "mọi tính toán đều giữ nguyên giá gốc trong menu mẫu."
        )
        rid = extracted.get("restaurant_id")
        members = extracted.get("members") or []
        if rid and members and all(m.get("budget_vnd") is not None for m in members):
            check = build_cart(rid, members, menu_cache=menu_cache)
            details = check.get("errors") or check.get("notices") or []
            if details:
                parts.append("Theo dữ liệu gốc: " + " ".join(details))
            parts.append("Không có giỏ hợp lệ trong ngân sách hiện tại.")
    if "private_profile_access" in flags:
        parts.append(
            "Mình không thể truy xuất, tiết lộ hay suy đoán hồ sơ ăn uống và lịch sử riêng của người khác từ cơ sở dữ liệu. "
            "Vui lòng hỏi trực tiếp hoặc để người đó tự cung cấp thông tin khi có sự đồng ý."
        )
    if "fake_live_verification" in flags:
        parts.append(
            "Mình không thể khẳng định đã xác minh trực tiếp giá, tồn kho hiện tại hay báo đơn đã đặt thành công. "
            "Menu, giá và tồn kho trong Lunchie là dữ liệu mẫu; người đặt cần kiểm tra trực tiếp trên ứng dụng rồi tự đặt."
        )
    if not parts:
        reason = str(extracted.get("reason") or "").strip()
        base = "Lunchie chỉ hỗ trợ lập giỏ cơm trưa từ menu mẫu. Mình không thể đặt hàng, thanh toán, bịa giá hoặc bỏ qua điều kiện an toàn."
        return f"{base} ({reason})" if reason else base
    return "\n".join(parts)


def _format_data_gap_response(extracted):
    gaps = extracted.get("data_gaps") or []
    parts = []
    if "unverifiable_food_attribute" in gaps:
        parts.append(
            "Menu mẫu hiện không có nhãn dinh dưỡng hay căn cứ đáng tin cậy để xác nhận tiêu chí món như vậy "
            "(không thể suy đoán chỉ từ tên món). Bạn hãy chọn tiêu chí khác có trong menu hoặc hỏi trực tiếp quán để xác nhận."
        )
    if "live_status_or_eta" in gaps:
        parts.append(
            "Dữ liệu mẫu chỉ có menu, giá và phí ship tham chiếu; không có giờ mở cửa hiện tại hay thời gian giao hàng (ETA) trực tiếp. "
            "Bạn hãy kiểm tra trạng thái mở cửa và thời gian giao trên ứng dụng; nếu muốn, mình vẫn có thể lập bản nháp giỏ món theo menu mẫu."
        )
    if not parts:
        reason = str(extracted.get("reason") or "").strip()
        return reason or "Chưa đủ căn cứ từ dữ liệu mẫu để kết luận; bạn có thể bổ sung tiêu chí có trong menu."
    return "\n".join(parts)


def _update_existing_cart(extracted, restaurant_id, text, menu_cache=None):
    members = extracted["members"]
    swap_name = _source_phrase(text, extracted.get("swap_member"))
    if not restaurant_id or not swap_name or not any(_norm(m["name"]) == _norm(swap_name) for m in members):
        return "Mình cần tên người muốn đổi món và quán của giỏ hiện tại."
    menu = _get_menu_cached(restaurant_id, menu_cache)
    if not menu["found"]:
        return menu["error"]
    selections = []
    before = None
    for member in members:
        current = _menu_match(menu["available_menu"] + menu["out_of_stock"], member["current_dish"])
        if current is None:
            return f"Mình cần tên hoặc mã món hiện tại của {member['name']} ở {restaurant_id} để giữ đúng các suất còn lại."
        selections.append(
            {
                "member_name": member["name"],
                "dish_id": current["dish_id"],
                "is_blind_bag": member["blind_bag"],
            }
        )
        if _norm(member["name"]) == _norm(swap_name):
            before = current
    feedback = extracted.get("swap_feedback") or text
    result = recommend_swap(restaurant_id, members, selections, swap_name, feedback)
    if not result["ok"]:
        return "Giữ nguyên giỏ hiện tại. " + " ".join(result["errors"])
    after = next(item for item in result["cart"]["items"] if _norm(item["member_name"]) == _norm(swap_name))
    change = (
        f"Đã đổi suất của {after['member_name']} từ {before['ten_mon']} sang {after['ten_mon']}. "
        "Các suất còn lại giữ nguyên."
    )
    return _format_cart(result["cart"], members, menu, notices=[change])


_SECOND_SWAP_RE = re.compile(
    r"\b(?:doi|quay xe)\b[^.!?\n]{0,60}?\b(?:lan|luot)\s*(?:2|hai|thu\s+(?:2|hai))\b"
    r"|\b(?:lan|luot)\s+thu\s+(?:2|hai)\b"
    r"|\bda\s+(?:doi|quay xe)(?:\s+mon)?\s+(?:1|mot)\s+(?:lan|luot)\b"
)

_ETA_DRAFT_PREFIX = (
    "Dữ liệu mẫu không có giờ mở cửa hay thời gian giao hàng (ETA) trực tiếp, nên mình không xác nhận được "
    "quán đang mở hoặc giao kịp giờ; hãy kiểm tra trên ứng dụng trước khi đặt. Dưới đây là bản nháp theo menu mẫu."
)


def _no_feasible_venue_message(members):
    """Explain why no sample venue fits the whole group, without silently drafting at an arbitrary venue."""
    restaurants = [r for r in _load_restaurants_data() if isinstance(r, dict) and r.get("restaurant_id")]
    n_members = max(1, len(members))
    reasons = []
    for member in members:
        relaxed = {**member, "budget_vnd": None}
        best = None
        for rest in restaurants:
            share = -(-int(rest.get("shipping_fee_vnd") or 0) // n_members)
            for dish in rest.get("menu") or []:
                if _dish_satisfies_member(dish, relaxed, share) is None:
                    total = int(dish["price_vnd"]) + share
                    if best is None or total < best[0]:
                        best = (total, dish, rest, share)
        budget = member.get("budget_vnd")
        if best is None:
            reasons.append(
                _allergy_guidance(member) if member.get("allergies")
                else f"Không quán mẫu nào có món thỏa điều kiện ăn uống của {member['name']}."
            )
        elif budget is not None and best[0] > budget:
            total, dish, rest, share = best
            reasons.append(
                f"{member['name']} cần tối thiểu {total:,}đ ({dish['ten_mon']} ở {rest['restaurant_id']}: "
                f"{int(dish['price_vnd']):,}đ + {share:,}đ phí ship mỗi người), vượt ngân sách {total - budget:,}đ."
            )
    if not reasons:
        reasons.append(
            "Từng người đều có món phù hợp ở một số quán, nhưng không quán nào đáp ứng được cả nhóm cùng lúc. "
            "Hãy chọn một quán để mình chỉ ra suất cần đổi."
        )
    return "Chưa tìm được quán phù hợp với ngân sách và điều kiện của cả nhóm. " + " ".join(reasons)


def run_text(text):
    normalized_raw = _norm(text)
    if re.search(
        r"\b(?:ngan sach|budget|toi da|muc chi)[^0-9\n-]{0,24}(?<![0-9.,])(?:-\s*\d+(?:[.,]\d{3})*|0)\s*(?:k|nghin|ngan|d|dong|vnd)\b",
        normalized_raw,
    ):
        return (
            "Ngân sách phải lớn hơn 0đ và đủ chi trả giá món cộng phí giao hàng chia đều. "
            "Hãy nhập hạn mức hợp lệ để mình kiểm tra giỏ."
        )
    if re.search(
        r"\b(?:chia\s+(?:doi|nua|deu)\s+(?:1|mot)\s+(?:hop|suat|phan)|(?:an|goi|dat|lay)\s+chung\s+(?:1|mot)\s+(?:hop|suat|phan))\b",
        normalized_raw,
    ):
        return (
            "Lunchie áp dụng định mức 1 suất riêng cho mỗi người (không hỗ trợ chia nửa suất hay ghép nhiều người vào 1 hộp). "
            "Hãy cho biết món hoặc ngân sách cho từng người."
        )

    menu_cache = {}
    extracted = extract_request(text)
    intent = extracted.get("intent")
    policy_flags = extracted.get("policy_flags") or []
    data_gaps = extracted.get("data_gaps") or []
    chosen = extracted.get("restaurant_id")
    note(f"route intent={intent} policy={policy_flags} gaps={data_gaps} rid={chosen}")

    if policy_flags or intent == "refuse":
        return _format_policy_response(extracted, menu_cache, text=text)

    normalized = _norm(text)
    if intent == "swap" and _SECOND_SWAP_RE.search(normalized):
        return "Mình không thể đổi món lần thứ hai cho cùng một người trong một giỏ. Giỏ hiện tại cần được giữ nguyên."

    if data_gaps:
        only_eta = set(data_gaps) == {"live_status_or_eta"}
        if not only_eta or extracted["missing_fields"] or not extracted["members"]:
            return _format_data_gap_response(extracted)
        drafted = _route_draft(extracted, text, menu_cache)
        if "Giỏ nháp tại" not in drafted:
            return _format_data_gap_response(extracted)
        note("eta_gap: draft kept with live-data disclaimer")
        return _ETA_DRAFT_PREFIX + "\n" + drafted

    if extracted["missing_fields"]:
        return "Mình cần bạn bổ sung: " + ", ".join(extracted["missing_fields"]) + "."

    return _route_draft(extracted, text, menu_cache)


def _route_draft(extracted, text, menu_cache):
    """Build (or swap) a validated draft once policy, data-gap and missing-field gates have passed."""
    members = extracted["members"]
    chosen = extracted.get("restaurant_id")
    normalized = _norm(text)
    if extracted.get("intent") == "swap":
        return _update_existing_cart(extracted, chosen, text, menu_cache=menu_cache)

    if chosen:
        menu = _get_menu_cached(chosen, menu_cache)
        if not menu.get("found"):
            return f"Quán {chosen} không có trong menu mẫu. Mình chưa tạo giỏ."
    else:
        restaurants = suggest_restaurants(members=members, max_results=3)
        if not restaurants:
            return _no_feasible_venue_message(members)
        chosen = restaurants[0]["restaurant_id"]

    recent = {_norm(m["name"]): m.get("recent_dish_name") for m in members if m.get("recent_dish_name")}
    result = build_cart(
        chosen,
        members,
        recent_by_member=recent,
        avoid_dishes=extracted.get("avoid_dishes"),
        menu_cache=menu_cache,
    )
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
    menu = _get_menu_cached(chosen, menu_cache) if explain else None
    return _format_cart(result["cart"], members, menu, explain=explain, notices=notices)
