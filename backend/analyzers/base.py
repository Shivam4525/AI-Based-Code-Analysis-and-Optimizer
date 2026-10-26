from abc import ABC, abstractmethod


class BaseAnalyzer(ABC):
    language: str = "unknown"

    @abstractmethod
    def analyze(self, code: str, filename: str = None) -> list:
        """
        Returns a list of issue dicts:
        {
            "category": "bug" | "security" | "performance" | "style",
            "severity": "Critical" | "High" | "Medium" | "Low",
            "line": int,
            "title": str,
            "description": str,
            "recommendation": str,
        }
        """
        raise NotImplementedError

    def safe_analyze(self, code: str, filename: str = None) -> list:
        """Wraps analyze() so one broken analyzer never crashes the whole request."""
        try:
            return self.analyze(code, filename)
        except Exception as e:
            return [{
                "category": "bug",
                "severity": "Low",
                "line": 0,
                "title": f"{self.language} analyzer error",
                "description": f"The analyzer failed to run: {str(e)}",
                "recommendation": "This is an internal analyzer issue, not necessarily a problem with your code.",
            }]