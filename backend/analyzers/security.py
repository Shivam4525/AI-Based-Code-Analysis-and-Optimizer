
import re
import hashlib


RULES = [
    {
        "id": "SEC001",
        "category": "security",
        "severity": "High",
        "title": "Possible SQL Injection",
        "pattern": re.compile(
            r"""(?:execute|executemany|query)\s*\(\s*["'`].*?(?:%s|%s|\.format\(|\+\s*[A-Za-z_$]|\$\{)""",
            re.IGNORECASE,
        ),
        "description": (
            "A database query may be constructed using dynamic input. "
            "This can allow an attacker to alter the intended SQL query."
        ),
        "impact": (
            "Depending on the query and database permissions, an attacker "
            "may read or modify unauthorized data."
        ),
        "recommendation": (
            "Use parameterized queries or prepared statements. "
            "Do not concatenate untrusted input into SQL."
        ),
    },
    {
        "id": "SEC002",
        "category": "security",
        "severity": "High",
        "title": "Possible Cross-Site Scripting (XSS)",
        "pattern": re.compile(
            r"""(?:\.innerHTML\s*=|insertAdjacentHTML\s*\(|document\.write\s*\()""",
            re.IGNORECASE,
        ),
        "description": (
            "This code writes HTML directly into a document. "
            "The operation can be unsafe when its content contains untrusted data."
        ),
        "impact": (
            "If attacker-controlled data reaches this operation, "
            "malicious JavaScript may execute in a user's browser."
        ),
        "recommendation": (
            "Use textContent for plain text. If HTML is required, "
            "sanitize it with a trusted HTML sanitizer."
        ),
    },
    {
        "id": "SEC003",
        "category": "security",
        "severity": "High",
        "title": "Possible Hardcoded Secret",
        "pattern": re.compile(
            r"""(?ix)
            \b(?:api[_-]?key|secret[_-]?key|access[_-]?token|
            auth[_-]?token|password|passwd|client[_-]?secret)\b
            \s*[:=]\s*
            (["'])(?!\s*(?:your[_ -].*|change[_ -]me|example|placeholder|xxx|<.*>))[^"'\r\n]{6,}\1
            """
        ),
        "description": (
            "A variable that may contain a credential or secret is assigned "
            "a string literal. The value may be sensitive."
        ),
        "impact": (
            "If the value is a real credential and the source code is shared, "
            "unauthorized users may gain access to a service or account."
        ),
        "recommendation": (
            "Load secrets from environment variables or a secret manager. "
            "Rotate the credential if a real secret was exposed."
        ),
    },
    {
        "id": "SEC004",
        "category": "security",
        "severity": "High",
        "title": "Unsafe Python Deserialization",
        "pattern": re.compile(
            r"""\bpickle\s*\.\s*loads?\s*\(""",
            re.IGNORECASE,
        ),
        "description": (
            "Python pickle deserialization can execute code when processing "
            "malicious serialized data."
        ),
        "impact": (
            "Untrusted serialized input may lead to arbitrary code execution."
        ),
        "recommendation": (
            "Never deserialize untrusted data with pickle. Prefer safer "
            "formats such as JSON when appropriate."
        ),
    },
    {
        "id": "SEC005",
        "category": "security",
        "severity": "High",
        "title": "Potentially Unsafe YAML Deserialization",
        "pattern": re.compile(
            r"""\byaml\s*\.\s*load\s*\(""",
            re.IGNORECASE,
        ),
        "description": (
            "yaml.load may construct unsafe objects depending on the loader "
            "and library version."
        ),
        "impact": (
            "Unsafe loading of untrusted YAML may execute unwanted behavior."
        ),
        "recommendation": (
            "Use yaml.safe_load for untrusted YAML where supported, and "
            "validate the resulting data."
        ),
    },
    {
        "id": "SEC006",
        "category": "security",
        "severity": "High",
        "title": "Dynamic Code Execution",
        "pattern": re.compile(
            r"""\b(?:eval\s*\(|exec\s*\(|new\s+Function\s*\()""",
            re.IGNORECASE,
        ),
        "description": (
            "This operation executes dynamically supplied code. "
            "Its safety depends on where the input originates."
        ),
        "impact": (
            "If an attacker can influence the input, arbitrary code may execute."
        ),
        "recommendation": (
            "Avoid dynamic code execution. Use explicit parsing, validation, "
            "or a restricted alternative."
        ),
    },
]


def scan_security(code: str, language: str = "unknown") -> list:
    """Run fast, deterministic security checks without executing user code."""
    findings = []
    lines = code.splitlines()

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip blank lines and common full-line comments.
        if not stripped or stripped.startswith(("#", "//", "--", "/*", "*")):
            continue

        for rule in RULES:
            # JavaScript dynamic-code checks are handled by ESLint,
            # which correctly ignores strings and comments.
            if (
                language.casefold() in {"javascript", "js"}
                and rule["id"] in {"SEC001", "SEC002", "SEC006"}
            ):
                continue

            if not rule["pattern"].search(line):
                continue

            evidence = stripped[:240]
            fingerprint_source = (
                f'{rule["id"]}:{line_number}:{evidence}'
            )
            fingerprint = hashlib.sha256(
                fingerprint_source.encode("utf-8")
            ).hexdigest()[:16]

            findings.append({
                "rule_id": rule["id"],
                "fingerprint": fingerprint,
                "category": rule["category"],
                "severity": rule["severity"],
                "line": line_number,
                "title": rule["title"],
                "description": rule["description"],
                "impact": rule["impact"],
                "evidence": evidence,
                "recommendation": rule["recommendation"],
                "verification_status": "not_applicable",
                "confidence": "medium",
                "language": language,
            })

    return findings
