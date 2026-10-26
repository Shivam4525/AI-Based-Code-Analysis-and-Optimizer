import json
import subprocess
import unittest
from pathlib import Path

XSS_SCRIPT = Path(__file__).resolve().parent / "js-tools" / "xss.js"


def scan(code):
    result = subprocess.run(
        ["node", str(XSS_SCRIPT)],
        input=code,
        text=True,
        capture_output=True,
        timeout=10,
        check=True,
    )
    return json.loads(result.stdout)


class TestXSSDetection(unittest.TestCase):
    def test_dynamic_document_write_detected(self):
        findings = scan("document.write(userInput);")
        self.assertTrue(any(f["kind"] == "document-write" for f in findings))

    def test_static_document_write_ignored(self):
        findings = scan('document.write("<p>Hello</p>");')
        self.assertFalse(any(f["kind"] == "document-write" for f in findings))

    def test_multiple_static_strings_ignored(self):
        findings = scan('document.write("<p>", "Hello", "</p>");')
        self.assertFalse(any(f["kind"] == "document-write" for f in findings))

    def test_inner_html_detected(self):
        findings = scan("element.innerHTML = userInput;")
        self.assertTrue(any(f["kind"] == "innerHTML-assignment" for f in findings))

    def test_insert_adjacent_html_detected(self):
        findings = scan('element.insertAdjacentHTML("beforeend", userInput);')
        self.assertTrue(any(f["kind"] == "insertAdjacentHTML" for f in findings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
