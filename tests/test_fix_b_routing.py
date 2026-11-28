"""Routing fixes after review (agent B): ETA keeps draft, half-portion scope, 2nd-swap cue, no-venue message."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

CODEBASE = Path(__file__).resolve().parents[1] / "codebase"
if str(CODEBASE) not in sys.path:
    sys.path.insert(0, str(CODEBASE))

import workflow  # noqa: E402


def _member(name, budget=60000, **overrides):
    member = {
        "name": name, "budget_vnd": budget, "allergies": [], "avoid_keywords": [], "vegetarian": False,
        "preferred_dish": "", "requested_dish": "", "dish_required": False, "current_dish": "", "blind_bag": False,
    }
    member.update(overrides)
    return member


def _extract(members, restaurant_id=None, intent="plan", **overrides):
    payload = {
        "reason": "ok", "policy_flags": [], "data_gaps": [], "intent": intent, "restaurant_id": restaurant_id,
        "members": members, "swap_member": None, "swap_feedback": "", "avoid_dishes": [], "missing_fields": [],
    }
    payload.update(overrides)
    return payload


def _fake_model(extract_payload):
    """Extraction returns the given payload; pick/swap calls choose the first allowed dish."""
    def call(system, user, schema=None, **_):
        if schema and schema["name"] == "lunch_request":
            payload = extract_payload
        else:
            data = json.loads(user)
            if "members" in data:
                payload = {"items": [
                    {"member_name": m["name"], "dish_id": m["eligible_dish_ids"][0]} for m in data["members"]
                ]}
            else:
                payload = {"items": [{"member_name": data["member_name"], "dish_id": data["options"][0]["dish_id"]}]}
        return {"text": json.dumps(payload, ensure_ascii=False), "model": "mock", "tokens_in": 1, "tokens_out": 1}
    return call


def _run(text, extract_payload):
    with mock.patch.object(workflow, "call_model", side_effect=_fake_model(extract_payload)):
        return workflow.run_text(text)


class TestEtaKeepsDraft(unittest.TestCase):
    def test_complete_order_with_delivery_time_still_drafts(self):
        out = _run(
            "Ở Q02 mỗi người tối đa 65k gồm ship: Vy thích cá, Nam ăn chay. Cần giao kịp trước 11h45.",
            _extract([_member("Vy", 65000, preferred_dish="cá"), _member("Nam", 65000, vegetarian=True)], "Q02"),
        )
        self.assertIn("Giỏ nháp tại", out)
        self.assertIn("ETA", out)
        self.assertLess(out.index("ETA"), out.index("Giỏ nháp tại"))

    def test_eta_only_question_without_budget_keeps_explanation(self):
        out = _run(
            "Quán Q05 giờ mở cửa mấy giờ, có giao kịp trưa nay không?",
            _extract([_member("An", None)], "Q05", intent="clarify", data_gaps=["live_status_or_eta"]),
        )
        self.assertNotIn("Giỏ nháp tại", out)
        self.assertIn("giờ mở cửa", out.lower())


class TestHalfPortionScope(unittest.TestCase):
    def test_extra_half_rice_is_not_refused(self):
        out = _run(
            "Q01 mỗi người tối đa 62k gồm ship: Hà muốn cơm thịt, lấy thêm nửa suất cơm; Quân ăn chay.",
            _extract([_member("Hà", 62000, preferred_dish="cơm thịt"), _member("Quân", 62000, vegetarian=True)], "Q01"),
        )
        self.assertNotIn("định mức 1 suất", out)
        self.assertIn("Giỏ nháp tại", out)

    def test_two_people_sharing_one_box_is_refused_without_model(self):
        with mock.patch.object(workflow, "call_model") as mocked:
            out = workflow.run_text("Hai đứa mình ăn chung một suất Phở gà ở Q03 cho tiết kiệm, tối đa 40k.")
        self.assertEqual(mocked.call_count, 0)
        self.assertIn("1 suất", out)


class TestSecondSwapCue(unittest.TestCase):
    def test_member_named_lan_with_amount_is_not_second_swap(self):
        out = _run(
            "Đổi món giỏ Q01: Lan đang có Cơm ngũ sắc chay, Lan 20k còn dư; Minh đang có Cơm gà xì dầu, Minh muốn đổi sang món gà không cay. Ai cũng tối đa 55k.",
            _extract(
                [_member("Lan", 55000, vegetarian=True, current_dish="Cơm ngũ sắc chay"),
                 _member("Minh", 55000, current_dish="Cơm gà xì dầu", avoid_keywords=["cay"])],
                "Q01", intent="swap", swap_member="Minh", swap_feedback="món gà không cay",
            ),
        )
        self.assertNotIn("lần thứ hai", out)

    def test_explicit_second_turn_still_blocked(self):
        out = _run(
            "Giỏ Q01: Hà đã đổi món một lần rồi, giờ Hà muốn đổi tiếp sang Cơm cuộn ba rọi xông khói.",
            _extract([_member("Hà", None, current_dish="Cơm gà xối mỡ")], "Q01", intent="swap", swap_member="Hà"),
        )
        self.assertIn("lần thứ hai", out)


class TestNoFeasibleVenue(unittest.TestCase):
    def test_no_venue_named_and_none_feasible_explains_instead_of_drafting(self):
        out = _run("Lập giỏ cho Bảo, tổng 18k đã gồm ship.", _extract([_member("Bảo", 18000)]))
        self.assertNotIn("Giỏ nháp tại", out)
        self.assertIn("Chưa tìm được quán", out)
        self.assertIn("Bảo cần tối thiểu", out)

    def test_named_venue_still_drafts_at_that_venue(self):
        out = _run("Ở Q06 cho Bảo, tối đa 70k gồm ship.", _extract([_member("Bảo", 70000)], "Q06"))
        self.assertIn("Giỏ nháp tại Bếp Phần Gọn", out)


if __name__ == "__main__":
    unittest.main()
