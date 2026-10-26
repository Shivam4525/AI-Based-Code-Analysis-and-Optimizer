from .python_analyzer import PythonAnalyzer
from .javascript_analyzer import JavaScriptAnalyzer

ANALYZER_REGISTRY = {
    "python": PythonAnalyzer(),
    "javascript": JavaScriptAnalyzer(),
}


def get_analyzer(language: str):
    return ANALYZER_REGISTRY.get(language)


def supported_languages():
    return list(ANALYZER_REGISTRY.keys())