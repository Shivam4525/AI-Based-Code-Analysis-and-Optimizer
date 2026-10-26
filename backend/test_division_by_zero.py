import unittest
from analyzers.javascript_logic_checks import find_division_by_zero_risks


class TestDivisionByZero(unittest.TestCase):
    def test_literal_zero_divisor_detected(self):
        issues = find_division_by_zero_risks("const result = 10 / 0;")
        self.assertTrue(any(i["title"] == "Division by zero" for i in issues))

    def test_zero_variable_detected(self):
        code = "const divisor = 0;\nconst result = 10 / divisor;"
        issues = find_division_by_zero_risks(code)
        self.assertTrue(any(i["title"] == "Possible division by zero" for i in issues))

    def test_reassigned_nonzero_variable_not_flagged(self):
        code = "let divisor = 0;\ndivisor = 2;\nconst result = 10 / divisor;"
        issues = find_division_by_zero_risks(code)
        self.assertFalse(any("division by zero" in i["title"].lower() for i in issues))

    def test_division_inside_string_ignored(self):
        code = 'const example = "10 / 0";'
        issues = find_division_by_zero_risks(code)
        self.assertEqual(issues, [])

    def test_division_inside_comment_ignored(self):
        code = "// const result = 10 / 0;"
        issues = find_division_by_zero_risks(code)
        self.assertEqual(issues, [])

    def test_normal_division_not_flagged(self):
        issues = find_division_by_zero_risks("const result = 10 / 2;")
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
