import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyzers.python_analyzer import PythonAnalyzer


class TestPythonAnalyzerSecurity(unittest.TestCase):
    def setUp(self):
        self.analyzer = PythonAnalyzer()

    def test_pickle_finding_preserves_rule_cwe_and_confidence(self):
        code = "import pickle\npickle.loads(user_data)\n"
        findings = [
            issue for issue in self.analyzer.analyze(code)
            if issue.get("rule_id") == "B301"
        ]

        self.assertTrue(findings, "Expected Bandit B301 finding")
        issue = findings[0]
        self.assertEqual(issue["category"], "security")
        self.assertEqual(issue["cwe_id"], 502)
        self.assertIn(issue["severity"], ("High", "Medium", "Low"))
        self.assertEqual(issue["confidence"], "HIGH")

    def test_pickle_import_finding_preserves_cwe(self):
        code = "import pickle\n"
        findings = [
            issue for issue in self.analyzer.analyze(code)
            if issue.get("rule_id") == "B403"
        ]

        self.assertTrue(findings, "Expected Bandit B403 finding")
        self.assertEqual(findings[0]["cwe_id"], 502)
        self.assertEqual(findings[0]["confidence"], "HIGH")


if __name__ == "__main__":
    unittest.main()
