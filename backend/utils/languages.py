LANGUAGE_MAP = {
    "python":     {"label": "Python",     "extensions": [".py"]},
    "javascript": {"label": "JavaScript", "extensions": [".js", ".jsx", ".mjs"]},
    "java":       {"label": "Java",       "extensions": [".java"]},
    "c":          {"label": "C",          "extensions": [".c", ".h"]},
    "cpp":        {"label": "C++",        "extensions": [".cpp", ".cc", ".cxx", ".hpp"]},
    "go":         {"label": "Go",         "extensions": [".go"]},
}

EXTENSION_TO_LANGUAGE = {
    ext: key for key, meta in LANGUAGE_MAP.items() for ext in meta["extensions"]
}

SUPPORTED_LANGUAGES = list(LANGUAGE_MAP.keys())