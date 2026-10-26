import unittest

from analyzers.registry import get_analyzer


class TestRescan(unittest.TestCase):
    def test_valid_code_has_no_undefined_name_errors(self):
        code = """
def calculate_total(price, quantity):
    return price * quantity
"""
        analyzer = get_analyzer("python")
        issues = analyzer.safe_analyze(code, "rescan_test.py")

        undefined_errors = [
            issue for issue in issues
            if "undefined" in (issue.get("title") or "").casefold()
            and (issue.get("severity") or "").casefold() in {"high", "critical"}
        ]

        self.assertEqual(
            undefined_errors,
            [],
            "Valid code should not produce undefined-name errors",
        )


if __name__ == "__main__":
    unittest.main()
