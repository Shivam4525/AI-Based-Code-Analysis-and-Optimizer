from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND))

from services.ollama import generate_explanation_and_fix
import subprocess

code = """
def save_order(cursor, username, total):
    try:
        query = "INSERT INTO orders (username, total) VALUES ('" + username + "', " + str(total) + ")"
        cursor.execute(query)
        cursor.connection.commit()
    except:
        pass
"""

issues = [
    {"category": "security", "severity": "High", "line": 3,
     "rule_id": "B608", "title": "Possible SQL injection",
     "description": "SQL is built using string concatenation."},
    {"category": "security", "severity": "Medium", "line": 6,
     "rule_id": "B110", "title": "Try, Except, Pass detected",
     "description": "Exceptions are silently ignored."},
]

print("Requesting focused fix from Ollama...")
result = generate_explanation_and_fix("python", code, issues)
fixed = result.get("fixed_code", "")

print("\n--- GENERATED CODE ---")
print(fixed or "(No code returned)")
if not fixed.strip():
    raise SystemExit("FAIL: Ollama returned empty code.")

path = Path("_ollama_focused_candidate.py")
path.write_text(fixed, encoding="utf-8")

print("\n--- SYNTAX CHECK ---")
try:
    compile(fixed, str(path), "exec")
    print("PASS: Python syntax")
except SyntaxError as exc:
    print(f"FAIL: Syntax error at line {exc.lineno}: {exc.msg}")
    raise SystemExit(1)

print("\n--- BANDIT SECURITY CHECK ---")
scan = subprocess.run(
    [sys.executable, "-m", "bandit", "-f", "txt", str(path)],
    capture_output=True, text=True, timeout=60,
)
print(scan.stdout)
if scan.stderr:
    print(scan.stderr)

print("\nNOTE: Manually review remaining security findings; syntax passing alone does not prove security.")
