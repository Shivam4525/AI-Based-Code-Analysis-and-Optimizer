import ast
import unittest

from services.ollama import generate_explanation_and_fix


class TestOllamaFix(unittest.TestCase):
    def test_undefined_variable_typo_is_fixed(self):
        code = """def calculate_total(price, quantity):
    return price * quantitty

print(calculate_total(100, 2))
"""
        issues = [
            {
                "severity": "High",
                "title": "Undefined variable 'quantitty'",
                "line": 2,
                "description": "Undefined variable quantitty",
            }
        ]

        result = generate_explanation_and_fix("python", code, issues)

        self.assertIsInstance(result, dict)
        self.assertIn("fixed_code", result)
        self.assertIn("explanation", result)

        fixed_code = result["fixed_code"]
        self.assertIsInstance(fixed_code, str)
        self.assertTrue(fixed_code.strip(), "AI returned empty code")

        # The returned code must at least be valid Python syntax.
        ast.parse(fixed_code)

        self.assertNotIn(
            "quantitty",
            fixed_code,
            "The reported variable typo remains in the generated code",
        )


if __name__ == "__main__":
    unittest.main()
