import unittest
from services.validation import validate_fixed_code


class TestFixedCodeValidation(unittest.TestCase):
    def test_valid_python_accepted(self):
        result = validate_fixed_code(
            "python",
            "def add(a, b):\n    return a + b",
        )
        self.assertTrue(result["valid"])
        self.assertEqual(
            result["verification_status"],
            "syntax_and_static_checks_passed",
        )

    def test_invalid_python_syntax_rejected(self):
        result = validate_fixed_code("python", "def add(:")
        self.assertFalse(result["valid"])
        self.assertEqual(result["verification_status"], "rejected")
        self.assertFalse(result["checks"]["syntax"])

    def test_empty_code_rejected(self):
        result = validate_fixed_code("python", "   ")
        self.assertFalse(result["valid"])
        self.assertEqual(result["verification_status"], "rejected")

    def test_undefined_python_name_rejected(self):
        result = validate_fixed_code(
            "python",
            "def add(a, b):\n    return a + missing_value",
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["verification_status"], "rejected")

    def test_unsupported_language_is_unverified(self):
        result = validate_fixed_code("ruby", "puts 'hello'")
        self.assertIsNone(result["valid"])
        self.assertEqual(result["verification_status"], "unverified")

    def test_valid_javascript_syntax(self):
        result = validate_fixed_code(
            "javascript",
            "function add(a, b) { return a + b; }",
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["verification_status"], "syntax_checked")


if __name__ == "__main__":
    unittest.main(verbosity=2)
