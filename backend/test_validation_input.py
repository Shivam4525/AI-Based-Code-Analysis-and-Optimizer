import unittest

from analyzers.security import scan_security


class TestValidationInput(unittest.TestCase):
    def test_unsafe_pickle_load_detected(self):
        code = """
import pickle
data = pickle.loads(user_input)
"""
        findings = scan_security(code, "python")
        self.assertTrue(findings, "Expected unsafe pickle loading to be detected")

    def test_unsafe_yaml_load_detected(self):
        code = """
import yaml
config = yaml.load(user_yaml)
"""
        findings = scan_security(code, "python")
        self.assertTrue(findings, "Expected unsafe YAML loading to be detected")

    def test_hardcoded_password_detected(self):
        code = '''
password = "MySecretPassword123"
'''
        findings = scan_security(code, "python")
        self.assertTrue(findings, "Expected hardcoded password to be detected")


if __name__ == "__main__":
    unittest.main()
