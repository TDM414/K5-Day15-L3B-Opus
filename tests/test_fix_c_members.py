"""Agent C fixes: shared predicates (T5), local allergy capture + synonyms (T7), attribute tags (T9)."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

CODEBASE = Path(__file__).resolve().parents[1] / "codebase"
if str(CODEBASE) not in sys.path:
    sys.path.insert(0, str(CODEBASE))

import tools  # noqa: E402
import workflow  # noqa: E402


def _m(name, budget=60000, **kw):
    base = dict(name=name, budget_vnd=budget, allergies=[], avoid_allergens=[], avoid_keywords=[],
                vegetarian=False, preferred_dish="", requested_dish="", dish_required=False,
                current_dish="", blind_bag=False)
    base.update(kw)
    return base


def _dish(dish_id):
    return next(d for r in tools._load_restaurants_data() for d in r["menu"] if d["dish_id"] == dish_id)


class TestSharedPredicate(unittest.TestCase):
    def test_names_joined_share_blind_cue_and_model_true_kept(self):
        ms = [_m("Khánh"), _m("Ly", blind_bag=True), _m("Vân", blind_bag=True), _m("Tâm", blind_bag=True)]
        workflow._augment_member_details("Khánh thích bò. Ly, Vân với Tâm thì sao cũng được, túi mù hết.", ms)
        self.assertEqual([m["blind_bag"] for m in ms], [False, True, True, True])

    def test_names_joined_share_vegetarian(self):
        ms = [_m("Ly"), _m("Vân"), _m("Khánh")]
        workflow._augment_member_details("Ly và Vân ăn chay, Khánh muốn gà", ms)
        self.assertEqual([m["vegetarian"] for m in ms], [True, True, False])

    def test_explicit_negation_clears_blind(self):
        ms = [_m("Ly", blind_bag=True), _m("Vân")]
        workflow._augment_member_details("Ly không phải túi mù, Vân gì cũng được", ms)
        self.assertEqual([m["blind_bag"] for m in ms], [False, True])

    def test_member_with_specific_dish_not_blind_when_other_is_blind(self):
        ms = [_m("Ly", blind_bag=True, current_dish="Cơm gà xì dầu"), _m("Vân", blind_bag=True)]
        workflow._augment_member_details("Ly có Cơm gà xì dầu, Vân gắn túi mù", ms)
        self.assertEqual([m["blind_bag"] for m in ms], [False, True])


class TestLocalAllergy(unittest.TestCase):
    def test_local_allergy_terms_split_and_stop(self):
        self.assertEqual(workflow._local_allergy_terms("Ngân dị ứng mè và sữa, muốn ăn bún"), ["mè", "sữa"])
        self.assertEqual(workflow._local_allergy_terms("Ngân không dị ứng gì cả"), [])
        self.assertEqual(workflow._local_allergy_terms("dị ứng tỏi ở Q02, ngân sách 50k"), ["tỏi"])

    def test_allergy_moved_out_of_avoid_keywords(self):
        ms = [_m("Ngân", avoid_keywords=["hành", "cay"])]
        workflow._augment_member_details("Ngân dị ứng hành, không ăn cay", ms)
        self.assertIn("hành", ms[0]["allergies"])
        self.assertNotIn("hành", ms[0]["avoid_keywords"])
        self.assertIn("cay", ms[0]["avoid_keywords"])

    def test_single_unnamed_member_uses_whole_text(self):
        ms = [_m("Người đặt")]
        workflow._augment_member_details("Một bạn dị ứng mực, đặt ở Q03 tối đa 60k", ms)
        self.assertIn("mực", ms[0]["allergies"])

    def test_peanut_synonym_blocks_dau_phong_dish(self):
        reason = tools._dish_satisfies_member(_dish("Q03-M04"), _m("An", 100000, allergies=["lạc"]), 0)
        self.assertTrue(reason)
        self.assertNotIn("cần xác nhận thành phần", reason)

    def test_allergy_never_becomes_kitchen_note(self):
        member = _m("An", allergies=["hành"], avoid_keywords=["hành lá"])
        self.assertEqual(tools._dish_garnish_notes(_dish("Q03-M11"), member), [])

    def test_misfiled_allergy_end_to_end_no_cart(self):
        extract = {
            "reason": "ok", "policy_flags": [], "data_gaps": [], "intent": "plan", "restaurant_id": "Q03",
            "members": [_m("Ngân", 70000, avoid_keywords=["hành"], requested_dish="Phở bò tái bò viên")],
            "swap_member": None, "swap_feedback": "", "avoid_dishes": [], "missing_fields": [],
        }
        reply = {"text": json.dumps(extract, ensure_ascii=False), "model": "m", "tokens_in": 1, "tokens_out": 1}
        with mock.patch.object(workflow, "call_model", return_value=reply):
            out = workflow.run_text("Ngân dị ứng hành, gọi Phở bò tái bò viên ở Q03 giúp, tối đa 70k")
        self.assertNotIn("Ghi chú quán", out)
        self.assertNotIn("Giỏ nháp tại", out)


class TestAttributeTags(unittest.TestCase):
    def test_spicy_reason_not_core_identity(self):
        spicy = next(d for d in tools.get_restaurant_menu("Q02")["available_menu"] if d.get("is_spicy"))
        reason = tools._dish_satisfies_member(spicy, _m("A", avoid_keywords=["cay"]), 5000)
        self.assertTrue(reason)
        self.assertNotIn("định danh", reason)


if __name__ == "__main__":
    unittest.main()
