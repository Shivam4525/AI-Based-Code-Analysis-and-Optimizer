from pathlib import Path
import sys
import subprocess

BACKEND = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND))

from services.ollama import (
    _split_into_chunks,
    _issues_for_chunk,
    generate_explanation_and_fix,
)

# More than 50 lines to exercise the chunked Python path.
code = "\n".join(
    [f"# Preserve this comment {i}" for i in range(1, 36)]
    + [
        "def save_order(cursor, username, total):",
        "    try:",
        '        query = "INSERT INTO orders (username, total) VALUES (\'" + username + "\', " + str(total) + ")"',
        "        cursor.execute(query)",
        "        cursor.connection.commit()",
        "    except:",
        "        pass",
    ]
    + [f"# trailing comment {i}" for i in range(1, 16)]
)

print("SOURCE LINES:", len(code.splitlines()))
chunks = _split_into_chunks(code, 40)
print("CHUNKS:", len(chunks))
print("CHUNK LINES:", [len(c.splitlines()) for c in chunks])
print("ALL LINES PRESERVED:",
      sum(len(c.splitlines()) for c in chunks) == len(code.splitlines()))

if sum(len(c.splitlines()) for c in chunks) != len(code.splitlines()):
    raise SystemExit("FAIL: source lines were lost.")

issues = [
    {
        "category": "security",
        "severity": "High",
        "line": 37,
        "rule_id": "B608",
        "title": "Possible SQL injection",
        "description": "SQL is built using string concatenation.",
    },
    {
        "category": "security",
        "severity": "Medium",
        "line": 42,
        "rule_id": "B110",
        "title": "Try, Except, Pass detected",
        "description": "Exceptions are silently ignored.",
    },
]

cursor = 1
for index, chunk in enumerate(chunks, 1):
    end = cursor + len(chunk.splitlines()) - 1
    matched = _issues_for_chunk(issues, cursor, end)
    print(f"CHUNK {index}: lines {cursor}-{end}; issues:",
          [(item["line"], item["rule_id"]) for item in matched])
    cursor = end + 1

print("\nRequesting chunked fix from Ollama...")
result = generate_explanation_and_fix("python", code, issues)
fixed = result.get("fixed_code") or ""
print("VERIFICATION STATUS:", result.get("verification_status"))
print("AI ERROR:", result.get("ai_error"))
print("FIXED CODE RETURNED:", bool(fixed.strip()))

if fixed.strip():
    candidate = Path("_ollama_chunked_candidate.py")
    candidate.write_text(fixed, encoding="utf-8")
    compile(fixed, str(candidate), "exec")
    print("SYNTAX CHECK: PASS")
    scan = subprocess.run(
        [sys.executable, "-m", "bandit", "-f", "txt", str(candidate)],
        capture_output=True, text=True, timeout=60,
    )
    print("BANDIT EXIT CODE:", scan.returncode)
    print(scan.stdout)
    if scan.stderr:
        print(scan.stderr)
else:
    print("No candidate accepted; inspect rejection details.")
    print("SECURITY REJECTION:", result.get("security_rejection_details"))
