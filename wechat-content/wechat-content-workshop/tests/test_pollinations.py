import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "content_workshop.py"
SPEC = importlib.util.spec_from_file_location("content_workshop_pollinations", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class PollinationsDecisionTests(unittest.TestCase):
    def test_with_pollinations_key_appends_query_parameter(self):
        url = MODULE.with_pollinations_key("https://gen.pollinations.ai/image/test?model=zimage", "sk_demo")
        self.assertIn("model=zimage", url)
        self.assertIn("key=sk_demo", url)

    def test_allowed_when_quota_is_available(self):
        decision = MODULE.decide_quota_strategy(
            MODULE.PollinationsQuotaStatus(
                ok=True,
                lines=[],
                key_data={"valid": True, "remainingBudget": 8},
                balance_data={"balance": 2},
            )
        )
        self.assertEqual(decision.status, "allowed")
        self.assertTrue(decision.allow_remote_generation)

    def test_auth_failed_when_key_marked_invalid(self):
        decision = MODULE.decide_quota_strategy(
            MODULE.PollinationsQuotaStatus(
                ok=True,
                lines=[],
                key_data={"valid": False},
                balance_data={"balance": 10},
            )
        )
        self.assertEqual(decision.status, "auth_failed")
        self.assertFalse(decision.allow_remote_generation)

    def test_quota_insufficient_when_balance_is_zero(self):
        decision = MODULE.decide_quota_strategy(
            MODULE.PollinationsQuotaStatus(
                ok=True,
                lines=[],
                key_data={"valid": True},
                balance_data={"balance": 0},
            )
        )
        self.assertEqual(decision.status, "quota_insufficient")
        self.assertFalse(decision.allow_remote_generation)

    def test_missing_key_when_precheck_reports_missing_key(self):
        decision = MODULE.decide_quota_strategy(
            MODULE.PollinationsQuotaStatus(
                ok=False,
                lines=[],
                errors=["missing_key:POLLINATIONS_API_KEY"],
            )
        )
        self.assertEqual(decision.status, "missing_key")
        self.assertFalse(decision.allow_remote_generation)

    def test_quota_check_failed_when_precheck_cannot_determine_quota(self):
        decision = MODULE.decide_quota_strategy(
            MODULE.PollinationsQuotaStatus(
                ok=False,
                lines=[],
                errors=["generation_failed:network:timeout"],
            )
        )
        self.assertEqual(decision.status, "quota_check_failed")
        self.assertTrue(decision.allow_remote_generation)


if __name__ == "__main__":
    unittest.main()
