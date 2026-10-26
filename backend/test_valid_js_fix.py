import sys
import unittest
from unittest.mock import patch
from flask import Flask

sys.path.insert(0, "backend")

from routes.analyze import analyze_bp


class FakeAnalyzer:
    def safe_analyze(self, code, filename=None):
        return []


class TestValidJavaScriptFixAccepted(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(analyze_bp)
        self.client = app.test_client()

    @patch("routes.analyze.get_user_from_token", return_value=None)
    @patch("routes.analyze.scan_security", return_value=[])
    @patch("routes.analyze.get_analyzer", return_value=FakeAnalyzer())
    @patch(
        "routes.analyze.fix_javascript",
        return_value=("function add(a, b) { return a + b; }", [], 1),
    )
    @patch("routes.analyze.get_risky_suggestions", return_value=[])
    @patch("routes.analyze.js_tools.node_check", return_value=(True, None))
    @patch("routes.analyze.get_explanation", return_value="Mock explanation")
    def test_valid_fix_passes_security_rescan(
        self,
        mock_explanation,
        mock_node_check,
        mock_risky,
        mock_fix,
        mock_analyzer,
        mock_scan_security,
        mock_user,
    ):
        response = self.client.post(
            "/api/analyze",
            json={
                "code": "function add(a, b) { return a - b; }",
                "filename": "test.js",
                "language": "javascript",
                "use_ai": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertEqual(
            data["verification_status"],
            "security_rescan_passed",
        )
        self.assertEqual(
            data["fixed_code"],
            "function add(a, b) { return a + b; }",
        )
        self.assertEqual(data["security_rejection_details"]["newly_detected"], [])

        print("\nPASS: Valid JavaScript fix was accepted.")
        print("PASS: Security re-scan passed.")
        print("PASS: No new security findings.")


if __name__ == "__main__":
    unittest.main(verbosity=2)

