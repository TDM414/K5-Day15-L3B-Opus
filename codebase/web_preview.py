"""Local web preview using the existing menu and cart checks."""

import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tools import (
    _dish_satisfies_member,
    get_restaurant_menu,
    suggest_restaurants,
    validate_cart,
)


WEB_ROOT = Path(__file__).with_name("web")


def cart_options(restaurant_id, members):
    menu = get_restaurant_menu(restaurant_id)
    if not menu["found"]:
        return {"error": menu["error"]}
    shipping = menu["shipping_fee_vnd"]
    share = (shipping + len(members) - 1) // len(members)
    return {
        "options": [
            [
                {"id": dish["dish_id"], "name": dish["ten_mon"], "price": dish["price_vnd"]}
                for dish in menu["available_menu"]
                if _dish_satisfies_member(dish, member, share) is None
            ]
            for member in members
        ],
    }


def preview_request(payload):
    members = payload.get("members")
    if not isinstance(members, list) or not members or any(
        not isinstance(member, dict)
        or type(member.get("budget_vnd")) is not int
        or member["budget_vnd"] <= 0
        or not str(member.get("name", "")).strip()
        for member in members
    ):
        return {"error": "Cần tên và ngân sách hợp lệ cho từng người."}

    action = payload.get("action")
    if action == "restaurants":
        return {"restaurants": suggest_restaurants(members)}
    if action == "options":
        return cart_options(payload.get("restaurant"), members)
    if action == "check":
        return validate_cart(payload.get("restaurant"), payload.get("selections"), members)
    return {"error": "Thao tác chưa được hỗ trợ."}


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
                self.send_error(400)
                return
            payload = json.loads(self.rfile.read(length))
            result = preview_request(payload) if isinstance(payload, dict) else {"error": "Yêu cầu không hợp lệ."}
        except (ValueError, UnicodeError):
            result = {"error": "Yêu cầu không hợp lệ."}
        response = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.send_response(400 if "error" in result else 200)
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
