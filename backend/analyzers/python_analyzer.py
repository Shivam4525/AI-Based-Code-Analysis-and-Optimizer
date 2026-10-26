
import ast
import subprocess
import json
import tempfile
import os
import sys

from .base import BaseAnalyzer


SEVERITY_MAP = {
    "error": "High",
    "warning": "Medium",
    "convention": "Low",
    "refactor": "Medium",
}


BANDIT_SEVERITY_MAP = {
    "HIGH": "High",
    "MEDIUM": "Medium",
    "LOW": "Low",
}



class PythonAnalyzer(BaseAnalyzer):
    language = "python"

    def analyze(self, code, filename=None):
        issues = self._check_syntax(code)

        # Further analysis cannot reliably continue with invalid syntax.
        if issues:
            return issues

        issues.extend(self._run_pylint(code))
        issues.extend(self._run_bandit(code))

        return issues

    def _tool_error(self, tool_name, message):
        """Report an incomplete tool scan instead of silently returning no findings."""
        return [{
            "category": "bug",
            "severity": "Low",
            "line": 0,
            "rule_id": f"{tool_name.lower()}-execution-error",
            "title": f"{tool_name} analysis could not complete",
            "description": (
                f"{message} Analysis results may be incomplete."
            ),
            "recommendation": (
                f"Check that {tool_name} is installed and working, "
                "then run the analysis again."
            ),
        }]

    def _check_syntax(self, code):
        try:
            ast.parse(code)
            return []
        except SyntaxError as e:
            return [{
                "category": "bug",
                "severity": "Critical",
                "line": e.lineno or 0,
                "title": "Syntax error",
                "description": str(e),
                "recommendation": (
                    "Fix the syntax error before further analysis can run."
                ),
            }]

    def _run_pylint(self, code):
        path = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".py",
                mode="w",
                delete=False,
                encoding="utf-8",
            ) as f:
                f.write(code)
                path = f.name

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pylint",
                    path,
                    "--output-format=json",
                    "--disable=C0114,C0116",
                ],
                capture_output=True,
                text=True,
                timeout=90,
            )

            # Pylint uses non-zero exit codes for ordinary findings too.
            # Its documented bit-flag exit codes range from 0 to 31.
            if result.returncode < 0 or result.returncode > 31:
                return self._tool_error(
                    "Pylint",
                    result.stderr.strip() or (
                        f"Pylint exited with code {result.returncode}."
                    ),
                )

            if not result.stdout.strip():
                if result.returncode != 0:
                    return self._tool_error(
                        "Pylint",
                        result.stderr.strip()
                        or "Pylint returned no analysis output.",
                    )
                return []

            raw = json.loads(result.stdout)

            if not isinstance(raw, list):
                return self._tool_error(
                    "Pylint",
                    "Pylint returned an unexpected JSON format.",
                )

            return [
                {
                    "category": (
                        "style"
                        if r.get("type") in ("convention", "refactor")
                        else "bug"
                    ),
                    "severity": SEVERITY_MAP.get(
                        r.get("type", ""),
                        "Low",
                    ),
                    "line": r.get("line", 0),
                    "rule_id": r.get("message-id") or r.get("symbol", ""),
                    "title": r.get("message", "Pylint finding"),
                    "description": (
                        f'{r.get("message", "")} '
                        f'(rule: {r.get("symbol", "unknown")})'
                    ),
                    "recommendation": {
                        "undefined-variable": (
                            "Define the variable before using it, "
                            "or correct its spelling."
                        ),
                        "unused-variable": (
                            "Remove the unused variable or use it "
                            "where intended."
                        ),
                        "unused-import": (
                            "Remove the import if it is not required."
                        ),
                        "no-else-return": (
                            "Remove the unnecessary else block after return."
                        ),
                        "no-duplicate-key": (
                            "Remove or correct the duplicate dictionary key."
                        ),
                        "missing-final-newline": (
                            "Add a newline at the end of the file."
                        ),
                        "trailing-whitespace": (
                            "Remove unnecessary spaces at the end of the line."
                        ),
                    }.get(
                        r.get("symbol", ""),
                        (
                            f'Check the "{r.get("symbol", "unknown")}" '
                            "rule and apply the suggested correction."
                        ),
                    ),
                }
                for r in raw
                if isinstance(r, dict)
            ]

        except subprocess.TimeoutExpired:
            return self._tool_error(
                "Pylint",
                "Analysis timed out after 90 seconds.",
            )
        except FileNotFoundError as e:
            return self._tool_error("Pylint", str(e))
        except (json.JSONDecodeError, UnicodeError) as e:
            return self._tool_error(
                "Pylint",
                f"Could not read analysis output: {e}",
            )
        except OSError as e:
            return self._tool_error("Pylint", str(e))
        finally:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

    def _run_bandit(self, code):
        path = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".py",
                mode="w",
                delete=False,
                encoding="utf-8",
            ) as f:
                f.write(code)
                path = f.name

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "bandit",
                    "-f",
                    "json",
                    path,
                ],
                capture_output=True,
                text=True,
                timeout=90,
            )

            if not result.stdout.strip():
                return self._tool_error(
                    "Bandit",
                    result.stderr.strip()
                    or (
                        f"Bandit returned no output "
                        f"(exit code {result.returncode})."
                    ),
                )

            raw = json.loads(result.stdout)

            if not isinstance(raw, dict):
                return self._tool_error(
                    "Bandit",
                    "Bandit returned an unexpected JSON format.",
                )

            findings = raw.get("results", [])

            if not isinstance(findings, list):
                return self._tool_error(
                    "Bandit",
                    "Bandit results were not in the expected format.",
                )

            issues = []

            for finding in findings:
                if not isinstance(finding, dict):
                    continue

                cwe = finding.get("issue_cwe") or {}
                if not isinstance(cwe, dict):
                    cwe = {}

                test_id = finding.get("test_id", "")
                test_name = finding.get("test_name", "")
                issue_text = finding.get("issue_text", "Security issue")

                issues.append({
                    "category": "security",
                    "severity": BANDIT_SEVERITY_MAP.get(
                        finding.get("issue_severity", "LOW"),
                        "Medium",
                    ),
                    "confidence": finding.get("issue_confidence", "UNKNOWN"),
                    "line": finding.get("line_number", 0),
                    "rule_id": test_id,
                    "title": issue_text,
                    "description": (
                        f"{issue_text} "
                        f"(CWE: {cwe.get('id', 'N/A')})"
                    ),
                    "cwe_id": cwe.get("id"),
                    "recommendation": (
                        f'Review Bandit rule "{test_id}" '
                        f"({test_name}) and address the vulnerability."
                    ),
                })

            # Bandit exit codes can be non-zero when findings exist.
            # Findings in valid JSON remain usable.
            return issues

        except subprocess.TimeoutExpired:
            return self._tool_error(
                "Bandit",
                "Security scan timed out after 90 seconds.",
            )
        except FileNotFoundError as e:
            return self._tool_error("Bandit", str(e))
        except (json.JSONDecodeError, UnicodeError) as e:
            return self._tool_error(
                "Bandit",
                f"Could not read security scan output: {e}",
            )
        except OSError as e:
            return self._tool_error("Bandit", str(e))
        finally:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
