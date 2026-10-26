import os
import re
from utils.languages import EXTENSION_TO_LANGUAGE
SCRIPT_TAG = re.compile(r'<script\b[^>]*>', re.I)

HTML_SIGNAL = re.compile(r'<!DOCTYPE\s+html|<html[\s>]', re.I)
CPP_SIGNALS = re.compile(r'\b(class\s+\w+|std::|template\s*<|namespace\s+\w+)\b')

CONTENT_HEURISTICS = [
    ("python", re.compile(r'^\s*(def |import |from .+ import|print\()', re.M)),
    ("go", re.compile(r'\b(func\s+\w+\s*\(|package\s+main)\b')),
    ("java", re.compile(r'\bpublic\s+(class|static\s+void\s+main)\b')),
    ("javascript", re.compile(r'\b(const |let |function\s+\w+\s*\(|=>)\b')),
    ("php", re.compile(r'<\?php')),
    ("sql", re.compile(r'\b(SELECT|INSERT INTO|UPDATE|DELETE FROM|CREATE TABLE)\b', re.I)),
    ("swift", re.compile(r'\b(func\s+\w+\s*\(|import\s+SwiftUI|import\s+Foundation)\b')),
    ("dart", re.compile(r'\b(void\s+main\s*\(|import\s+[\'"]package:)\b')),
    ("csharp", re.compile(r'\b(using\s+System|namespace\s+\w+|public\s+class)\b')),
]


def detect_language(filename: str = None, code: str = "") -> str:
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        lang = EXTENSION_TO_LANGUAGE.get(ext)
        if lang == "c" and ext == ".h" and CPP_SIGNALS.search(code):
            return "cpp"
        if lang:
            return lang
        if ext in (".html", ".htm") and SCRIPT_TAG.search(code):
            return "javascript"

    # No filename, but the content itself looks like an HTML page with a <script> block
    if HTML_SIGNAL.search(code) and SCRIPT_TAG.search(code):
        return "javascript"

    for lang, pattern in CONTENT_HEURISTICS:
        if pattern.search(code):
            return lang

    return "unknown"