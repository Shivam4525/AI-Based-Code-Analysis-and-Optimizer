import sys
import unittest
from unittest.mock import patch
from flask import Flask

sys.path.insert(0, "backend")

from routes.analyze import analyze_bp


class FakeAnalyzer:
    def safe_analyze(self, code, filename=None):
        return []


class TestJavaScriptFixRejection(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.register_blueprint(analyze_bp)
        self.client = app.test_client()

    @patch("routes.analyze.get_user_from_token", return_value=None)
    @patch("routes.analyze.scan_security", return_value=[])
    @patch("routes.analyze.get_analyzer", return_value=FakeAnalyzer())
    @patch(
        "routes.analyze.fix_javascript",
        return_value=("function broken( {", [], 1),
    )
    @patch("routes.analyze.get_risky_suggestions", return_value=[])
    @patch(
        "routes.analyze.js_tools.node_check",
        return_value=(False, "Mock syntax error"),
    )
    def test_invalid_javascript_fix_is_rejected(
        self,
        mock_node_check,
        mock_risky,
        mock_fix,
        mock_analyzer,
        mock_security,
        mock_user,
    ):
        response = self.client.post(
            "/api/analyze",
            json={
                "code": "function add(a, b) { return a + b; }",
                "filename": "test.js",
                "language": "javascript",
                "use_ai": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertIsNone(data["fixed_code"])
        self.assertIn("syntax validation failed", data["ai_error"])
        self.assertEqual(data["verification_status"], "not_run")
        mock_node_check.assert_called_once()

        print("\nPASS: Invalid JavaScript fix was rejected.")
        print("PASS: fixed_code is null.")
        print("PASS: Syntax failure is reported.")
        print("PASS: Ollama was not needed.")


if __name__ == "__main__":
    unittest.main(verbosity=2)

