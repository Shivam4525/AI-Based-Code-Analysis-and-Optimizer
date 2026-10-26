import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyzers.javascript_analyzer import JavaScriptAnalyzer


class TestJavaScriptSecurityRules(unittest.TestCase):
    def setUp(self):
        self.analyzer = JavaScriptAnalyzer()

    def security_findings(self, code):
        return [
            issue
            for issue in self.analyzer.analyze(code)
            if issue["category"] == "security"
        ]

    def test_hardcoded_secret_has_cwe(self):
        findings = self.security_findings(
            'const password = "example-secret";'
        )
        issue = next(
            (item for item in findings
             if item.get("rule_id") == "custom/hardcoded-secret"),
            None,
        )
        self.assertIsNotNone(issue)
        self.assertEqual(issue["cwe_id"], 798)

    def test_sql_injection_has_cwe(self):
        findings = self.security_findings(
            'const query = "SELECT * FROM users WHERE name = " + userInput;'
        )
        issue = next(
            (item for item in findings
             if item.get("rule_id") == "custom/sql-injection"),
            None,
        )
        self.assertIsNotNone(issue)
        self.assertEqual(issue["cwe_id"], 89)

    def test_weak_hash_has_cwe(self):
        findings = self.security_findings(
            'const hash = createHash("md5");'
        )
        issue = next(
            (item for item in findings
             if item.get("rule_id") == "custom/weak-hash"),
            None,
        )
        self.assertIsNotNone(issue)
        self.assertEqual(issue["cwe_id"], 327)

    def test_xss_has_cwe(self):
        findings = self.security_findings(
            'element.innerHTML = userInput;'
        )
        issue = next(
            (item for item in findings
             if item.get("rule_id") == "custom/dom-xss"),
            None,
        )
        self.assertIsNotNone(issue)
        self.assertEqual(issue["cwe_id"], 79)


if __name__ == "__main__":
    unittest.main()
