import sys
import unittest
from unittest.mock import patch

from flask import Flask

sys.path.insert(0, "backend")

from routes.analyze import analyze_bp


class FakeAnalyzer:
    def safe_analyze(self, code, filename=None):
        return []


class TestNewSecurityFindingRejected(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(analyze_bp)
        self.client = app.test_client()

    @patch("routes.analyze.get_user_from_token", return_value=None)
    @patch("routes.analyze.scan_security")
    @patch("routes.analyze.get_analyzer", return_value=FakeAnalyzer())
    @patch(
        "routes.analyze.fix_javascript",
        return_value=(
            "const output = location.hash; "
            "document.body.innerHTML = output;",
            [],
            1,
        ),
    )
    @patch("routes.analyze.get_risky_suggestions", return_value=[])
    @patch("routes.analyze.js_tools.node_check", return_value=(True, None))
    @patch("routes.analyze.get_explanation", return_value="Mock explanation")
    def test_new_security_finding_rejects_candidate(
        self,
        mock_explanation,
        mock_node_check,
        mock_risky,
        mock_fix,
        mock_analyzer,
        mock_scan_security,
        mock_user,
    ):
        mock_scan_security.side_effect = [
            [],
            [
                {
                    "category": "security",
                    "severity": "High",
                    "line": 1,
                    "title": "Test: unsafe HTML injection",
                    "description": "Mocked security finding.",
                    "recommendation": "Use textContent.",
                    "rule_id": "TEST_XSS",
                }
            ],
        ]

        response = self.client.post(
            "/api/analyze",
            json={
                "code": "const output = 'safe';",
                "filename": "test.js",
                "language": "javascript",
                "use_ai": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        # The candidate must not be returned as accepted code.
        self.assertIsNone(data["fixed_code"])
        self.assertEqual(data["fixed_issues"], [])

        # Security verification must explicitly show rejection.
        self.assertEqual(
            data["verification_status"],
            "rejected_security_check",
        )
        self.assertIn(
            "additional security findings",
            data["ai_error"].casefold(),
        )

        # Explanation must agree with the rejection status.
        self.assertIn(
            "rejected",
            data["ai_explanation"].casefold(),
        )
        self.assertNotIn(
            "passed the security re-scan",
            data["ai_explanation"].casefold(),
        )

        # The newly detected security issue must be reported.
        rejection_details = data["security_rejection_details"]
        self.assertTrue(rejection_details["newly_detected"])
        self.assertEqual(
            rejection_details["newly_detected"][0]["rule_id"],
            "TEST_XSS",
        )

        print("\nPASS: New security finding rejects the candidate.")
        print("PASS: fixed_code is null and fixed_issues is empty.")
        print("PASS: Verification status reports rejection.")
        print("PASS: Explanation agrees with rejection status.")
        print("PASS: Rejection details include TEST_XSS.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
