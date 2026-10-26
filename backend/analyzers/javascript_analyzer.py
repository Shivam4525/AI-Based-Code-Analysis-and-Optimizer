import re
from .base import BaseAnalyzer
from services import js_tools
from .javascript_logic_checks import find_division_by_zero_risks

def find_obvious_nan_risks(code):
    """Detect obvious numeric operations using quoted non-numeric strings."""
    issues = []
    pattern = re.compile(
    r"""(?:(?P<left>["'](?:[A-Za-z_][A-Za-z0-9_ ]*)["'])\s*[*+\-/]\s*\d+|\d+\s*[*+\-/]\s*(?P<right>["'](?:[A-Za-z_][A-Za-z0-9_ ]*)["']))"""
    )

    for line_no, line in enumerate(code.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith(("//", "/*", "*")):
            continue

        for match in pattern.finditer(line):
            value = match.group("left") or match.group("right")
            issues.append(_issue(
                "bug",
                "Medium",
                line_no,
                "Possible NaN from non-numeric string in arithmetic",
                f"The value {value} appears to be used in a numeric operation. "
                "JavaScript may produce NaN or an unexpected result.",
                "Validate and convert the input with Number(), then check "
                "Number.isFinite() before performing arithmetic.",
            ))

    return issues

SECURITY_RULES = {"no-eval", "no-implied-eval", "no-new-func", "no-script-url"}
PERFORMANCE_RULES = {"no-await-in-loop", "no-loop-func"}
STYLE_RULES = {
    "no-unused-vars", "no-var", "prefer-const", "eqeqeq", "curly",
    "no-shadow", "no-empty", "no-extra-semi", "no-useless-escape",
}
CRITICAL_RULES = {"no-eval", "no-implied-eval", "no-new-func", "security/detect-eval-with-expression"}
HIGH_SECURITY_RULES = {
    "security/detect-child-process", "security/detect-non-literal-require",
    "security/detect-unsafe-regex", "security/detect-buffer-noassert",
    "security/detect-new-buffer", "security/detect-pseudoRandomBytes",
}

RECOMMENDATIONS = {
    "no-undef": "Define or import this identifier, or pass it in as a parameter â€” never rely on an undeclared global.",
    "no-unused-vars": "Remove the unused variable/function, or actually use it.",
    "no-var": "Use const (or let if it is reassigned) instead of var.",
    "prefer-const": "Declare it with const since it is never reassigned.",
    "eqeqeq": "Use === / !== to avoid implicit type coercion.",
    "curly": "Always wrap if/else/loop bodies in braces.",
    "no-eval": "Never execute strings as code â€” call the logic directly, or use JSON.parse for data.",
    "no-implied-eval": "Pass a function to setTimeout/setInterval instead of a string.",
    "no-new-func": "Avoid new Function(); write the logic as a normal function.",
    "no-await-in-loop": "Run independent awaits in parallel with Promise.all(items.map(...)).",
    "no-loop-func": "Move the function out of the loop body.",
    "no-shadow": "Rename the inner variable so it does not shadow the outer one.",
    "no-empty": "Handle the case, or add a comment explaining why the block is intentionally empty.",
}

SECRET_ASSIGN = re.compile(
    r"\b(?P<name>\w*(?:password|passwd|pwd|secret|api_?key|token|private_?key)\w*)"
    r"\s*[:=]\s*(?P<q>[\"'])(?P<val>[^\"'\n]{4,})(?P=q)", re.I,
)
AWS_KEY = re.compile(r"AKIA[0-9A-Z]{16}")
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
SQL_STMT = re.compile(r"\b(select\b.+\bfrom|insert\s+into|update\b.+\bset|delete\s+from)\b", re.I)
CONCAT = re.compile(r"[\"'`]\s*\+|\+\s*[\"'`]|\$\{")

WEAK_HASH = re.compile(
    r"""(?:createHash\s*\(\s*["'](?:md5|sha1)["']|"""
    r"""\b(?:md5|sha1)\s*\()""",
    re.I,
)

INNER_HTML = re.compile(r"\.innerHTML\s*=(?!=)|document\.write(?:ln)?\s*\(|dangerouslySetInnerHTML")


def _category(rule):
    if rule.startswith("security/") or rule in SECURITY_RULES:
        return "security"
    if rule in PERFORMANCE_RULES:
        return "performance"
    if rule in STYLE_RULES:
        return "style"
    return "bug"


def _severity(rule, eslint_severity, category):
    if rule in CRITICAL_RULES:
        return "Critical"
    if rule in HIGH_SECURITY_RULES:
        return "High"
    if category == "security":
        return "Medium"
    if category == "style":
        return "Low"
    if category == "performance":
        return "Medium"
    return "High" if eslint_severity == 2 else "Medium"


def _issue(category, severity, line, title, description, recommendation):
    return {
        "category": category, "severity": severity, "line": line,
        "title": title, "description": description, "recommendation": recommendation,
    }


class JavaScriptAnalyzer(BaseAnalyzer):
    language = "javascript"

    def analyze(self, code, filename=None):
        messages, err = js_tools.eslint_messages(code)
        if err:
            return [_issue(
                "bug", "Low", 0, "ESLint could not run", err,
                "Check that Node.js and ESLint are installed correctly in backend/js-tools.",
            )]

        fatal = [m for m in messages if m.get("fatal")]
        if fatal:
            m = fatal[0]
            return [_issue(
                "bug", "Critical", m.get("line", 0), "Syntax error", m.get("message", ""),
                "Fix the syntax error before further analysis can run.",
            )]

        issues = []
        eval_lines = {m.get("line") for m in messages if m.get("ruleId") == "no-eval"}

        for m in messages:
            rule = m.get("ruleId") or ""
            line = m.get("line", 0)
            if rule == "security/detect-eval-with-expression" and line in eval_lines:
                continue  # same problem already reported by no-eval
            category = _category(rule)
            issues.append(_issue(
                category, _severity(rule, m.get("severity", 1), category), line,
                m.get("message", "ESLint issue"),
                f'{m.get("message", "")} (rule: {rule})',
                RECOMMENDATIONS.get(rule, f'Review ESLint rule "{rule}" and adjust the code accordingly.'),
            ))
            issues[-1]["rule_id"] = rule

        issues += self._performance_findings(code)
        issues += self._pattern_security(code)
        issues += find_division_by_zero_risks(code)
        issues += find_obvious_nan_risks(code)
        return self._dedupe(issues)

    def _performance_findings(self, code):
        issues = []
        for f in js_tools.extra_findings(code):
            if f["kind"] == "nested-loop":
                issues.append(_issue(
                    "performance", "Medium", f["line"],
                    "Nested loop detected (potential O(nÂ²) complexity)",
                    "A loop inside another loop grows quadratically with input size.",
                    "Index one collection in a Map/Set first, then do a single pass with O(1) lookups.",
                ))
            elif f["kind"] == "lookup-in-loop":
                issues.append(_issue(
                    "performance", "Low", f["line"],
                    f".{f['method']}() called inside a loop (repeated linear scans)",
                    "Each iteration rescans the whole array, which is O(nÂ²) overall.",
                    "Build a Set/Map once outside the loop and use .has()/.get() inside it.",
                ))
        return issues

    def _pattern_security(self, code):
        issues = []
        for no, line in enumerate(code.split("\n"), start=1):
            stripped = line.strip()
            if stripped.startswith(("//", "*", "/*")):
                continue

            m = SECRET_ASSIGN.search(line)
            
            if m:
                issue = _issue(
                    "security",
                    "Medium",
                    no,
                    f"Possible hardcoded secret: '{m.group('name')}'",
                    "Hardcoded credentials end up in source control and builds (CWE-798).",
                    "Load it from an environment variable (process.env.NAME) or a secrets manager.",
                )
                issue["rule_id"] = "custom/hardcoded-secret"
                issue["cwe_id"] = 798
                issues.append(issue)

            
            if AWS_KEY.search(line) or PRIVATE_KEY.search(line):
                issue = _issue(
                    "security",
                    "High",
                    no,
                    "Hardcoded cloud key / private key detected",
                    "A real-looking access key or private key is embedded in the source (CWE-798).",
                    "Revoke and rotate this key immediately, then load it from the environment.",
                )
                issue["rule_id"] = "custom/hardcoded-key"
                issue["cwe_id"] = 798
                issues.append(issue)

            
            if SQL_STMT.search(line) and CONCAT.search(line):
                issue = _issue(
                    "security",
                    "High",
                    no,
                    "Possible SQL injection: query built with string concatenation/interpolation",
                    "User input placed directly into SQL text can change the query (CWE-89).",
                    "Use parameterized queries: placeholders in the SQL and a separate values array.",
                )
                issue["rule_id"] = "custom/sql-injection"
                issue["cwe_id"] = 89
                issues.append(issue)

            
            if WEAK_HASH.search(line):
                issue = _issue(
                    "security",
                    "High",
                    no,
                    "Use of weak hash algorithm (MD5/SHA-1)",
                    "MD5 and SHA-1 are broken for security purposes (CWE-327).",
                    "Use SHA-256 or better; for passwords use bcrypt/argon2/scrypt.",
                )
                issue["rule_id"] = "custom/weak-hash"
                issue["cwe_id"] = 327
                issues.append(issue)

       
        # AST-based DOM XSS detection (avoids strings/comments false positives)
        for finding in js_tools.xss_nodes(code):
            issue = _issue(
                "security",
                "Medium",
                finding["line"],
                "Possible XSS: raw HTML injection into the page",
                "Dynamic data written as HTML may allow script injection (CWE-79).",
                "Use textContent for plain text, or sanitize untrusted HTML before inserting it.",
            )
            issue["rule_id"] = "custom/dom-xss"
            issue["cwe_id"] = 79
            issues.append(issue)


        return issues

    @staticmethod
    def _dedupe(issues):
        seen, unique = set(), []
        for i in issues:
            key = (i["category"], i["line"], i["title"])
            if key not in seen:
                seen.add(key)
                unique.append(i)
        return unique
