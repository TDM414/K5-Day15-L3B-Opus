"""Local web preview using the existing menu and cart checks."""

import argparse
import json
import threading
import uuid
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ai import ModelError
from tools import suggest_restaurants, validate_cart
from workflow import _norm, build_cart, extract_request, recommend_swap
from storage import finalize as save_finalized_cart, list_members, list_orders


WEB_ROOT = Path(__file__).with_name("web")
DRAFTS = {}
DRAFTS_LOCK = threading.RLock()


def draft_view(draft):
    return {
        "draft_id": draft["id"],
        "revision": draft["revision"],
        "cart": draft["cart"],
        "options": draft["options"],
        "menu": draft["menu"],
        "selections": draft["selections"],
        "notices": draft["notices"],
        "changed_members": sorted(draft["changed"]),
        "finalized": draft["finalized"],
    }


def menu_item_view(dish):
    return {
        "id": dish["dish_id"],
        "name": dish["ten_mon"],
        "price": dish.get("price_vnd"),
        "image_url": dish.get("image_url"),
        "in_stock": dish["in_stock"],
    }


def create_draft(restaurant_id, members):
    recent = {}
    for order in list_orders():
        for item in order["items"]:
            recent.setdefault(_norm(item["member_name"]), item["dish_id"])
    result = build_cart(restaurant_id, members, recent)
    if not result["ok"]:
        return {"error": " ".join(result["errors"])}
    draft_id = uuid.uuid4().hex
    menu = result["menu"]
    draft = {
        "id": draft_id,
        "lock": threading.Lock(),
        "restaurant_id": result["cart"]["restaurant_id"],
        "members": members,
        "cart": result["cart"],
        "options": [[menu_item_view(dish) for dish in group] for group in result["replacement_options"]],
        "menu": [menu_item_view(dish) for dish in menu["available_menu"] + menu["out_of_stock"]],
        "selections": [
            {key: item[key] for key in ("member_name", "dish_id", "is_blind_bag")}
            for item in result["cart"]["items"]
        ],
        "notices": result["notices"],
        "changed": set(),
        "revision": 1,
        "finalized": False,
    }
    with DRAFTS_LOCK:
        DRAFTS[draft_id] = draft
    return draft_view(draft)


def edit_draft(action, payload, draft):
    if action == "finalize" and draft["finalized"]:
        return {**draft_view(draft), "order": draft["cart"]}
    if payload.get("revision") != draft["revision"] or draft["finalized"]:
        return {
            "error": "Giỏ đã thay đổi. Kiểm tra lại phiên bản mới nhất.",
            "code": "draft_conflict",
            "draft": draft_view(draft),
        }
    if action == "finalize":
        checked = validate_cart(draft["restaurant_id"], draft["selections"], draft["members"])
        if not checked["ok"]:
            return {
                "error": " ".join(checked["errors"]) + " Hãy dựng lại giỏ để kiểm tra theo menu hiện tại.",
                "code": "draft_invalid",
            }
        draft["cart"] = save_finalized_cart(
            draft["id"], checked, draft["members"], payload.get("save_profiles") is True
        )
        draft["finalized"] = True
        draft["revision"] += 1
        return {**draft_view(draft), "order": draft["cart"]}

    selections = draft["selections"]
    if action == "check":
        submitted = payload.get("selections")
        if not isinstance(submitted, list) or len(submitted) != len(selections):
            return {"error": "Số suất không khớp giỏ nháp."}
        new_dishes = {s.get("member_name"): s.get("dish_id") for s in submitted
                      if isinstance(s, dict) and isinstance(s.get("member_name"), str)}
        if new_dishes.keys() != {s["member_name"] for s in selections}:
            return {"error": "Không thể đổi tên hoặc thêm/bớt thành viên sau khi dựng giỏ."}
        changes = [i for i, s in enumerate(selections) if new_dishes[s["member_name"]] != s["dish_id"]]
        if len(changes) != 1:
            return {"error": "Mỗi thao tác chỉ đổi một suất."}
        index = changes[0]
    else:
        member_name = _norm(payload.get("member_name"))
        index = next((i for i, s in enumerate(selections) if _norm(s["member_name"]) == member_name), None)
        if index is None:
            return {"error": "Không xác định được thành viên cần đổi món."}

    member_name = selections[index]["member_name"]
    if member_name in draft["changed"]:
        return {"error": "Thành viên này đã dùng lượt đổi món duy nhất."}
    alternatives = {dish["id"] for dish in draft["options"][index]} - {selections[index]["dish_id"]}
    if not alternatives:
        return {"error": f"Chưa có món thay thế phù hợp cho {member_name}."}

    if action == "swap":
        result = recommend_swap(
            draft["restaurant_id"], draft["members"], selections, member_name, payload.get("feedback"),
            allowed_dish_ids=alternatives,
        )
        if not result["ok"]:
            return {"error": " ".join(result["errors"])}
        checked = result["cart"]
        updated = result["selections"]
    else:
        dish_id = new_dishes[member_name]
        if not isinstance(dish_id, str) or dish_id not in alternatives:
            return {"error": f"Món thay thế chưa đáp ứng yêu cầu của {member_name}."}
        updated = list(selections)
        updated[index] = {**selections[index], "dish_id": dish_id}
        checked = validate_cart(draft["restaurant_id"], updated, draft["members"])
        if not checked["ok"]:
            return {"error": " ".join(checked["errors"])}
    draft["cart"] = checked
    draft["selections"] = updated
    draft["changed"].add(member_name)
    draft["revision"] += 1
    return draft_view(draft)


def preview_request(payload):
    action = payload.get("action")
    if action == "parse":
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            return {"error": "Dán tin nhắn nhóm hoặc chọn Nhập thủ công."}
        return extract_request(text, payload.get("shared_budget_vnd"))
    if action in ("profiles", "history", "saved"):
        saved = {}
        if action != "history":
            saved["members"] = list_members()
        if action != "profiles":
            saved["orders"] = list_orders()
        return saved
    if action in ("check", "swap", "finalize"):
        draft_id = payload.get("draft_id")
        with DRAFTS_LOCK:
            draft = DRAFTS.get(draft_id) if isinstance(draft_id, str) else None
        if not draft:
            return {"error": "Giỏ nháp đã hết hiệu lực. Hãy dựng lại giỏ.", "code": "draft_missing"}
        with draft["lock"]:
            return edit_draft(action, payload, draft)
    if action not in ("restaurants", "options"):
        return {"error": "Thao tác chưa được hỗ trợ."}

    members = payload.get("members")
    if not isinstance(members, list) or not members or any(
        not isinstance(member, dict)
        or type(member.get("budget_vnd")) is not int
        or member["budget_vnd"] <= 0
        or not isinstance(member.get("name"), str)
        or not member["name"].strip()
        or (member.get("dish_required") and not (
            str(member.get("requested_dish") or member.get("preferred_dish") or "").strip()
        ))
        or any(not isinstance(member.get(field, []), list)
               or not all(isinstance(term, str) for term in member.get(field, []))
               for field in ("allergies", "avoid_keywords", "avoid_allergens"))
        for member in members
    ):
        return {"error": "Cần tên, ngân sách và điều kiện ăn uống hợp lệ cho từng người."}
    members = [{**member, "name": member["name"].strip()} for member in members]
    if len({_norm(member["name"]) for member in members}) != len(members):
        return {"error": "Tên bị trùng. Thêm họ hoặc biệt danh để phân biệt từng người."}
    if action == "restaurants":
        return {"restaurants": suggest_restaurants(members, require_exact_dishes=True)}
    return create_draft(payload.get("restaurant"), members)


class PreviewHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/preview":
            self.send_error(404)
            return
        host = self.headers.get("Host")
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{host}":
            self.send_error(403)
            return
        if self.headers.get_content_type() != "application/json":
            self.send_error(415)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 128_000:
                raise ValueError
            payload = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeError):
            payload = None
        try:
            result = preview_request(payload) if isinstance(payload, dict) else {"error": "Yêu cầu không hợp lệ."}
            status = {"draft_conflict": 409, "draft_invalid": 409, "draft_missing": 410}.get(
                result.get("code"), 400 if "error" in result else 200
            )
        except ModelError as exc:
            status = 502
            result = {"error": str(exc), "code": "retry"}
        except Exception as exc:
            self.log_error("Preview request failed (%s)", type(exc).__name__)
            status = 500
            result = {"error": "Máy chủ chưa xử lý được yêu cầu. Hãy thử lại.", "code": "retry"}
        response = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(response)


def serve():
    parser = argparse.ArgumentParser(description="Chạy Lunchie trên máy.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    handler = partial(PreviewHandler, directory=str(WEB_ROOT))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    except OSError:
        if args.port != 8000:
            raise
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    with server:
        print(f"Mở Lunchie tại http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
