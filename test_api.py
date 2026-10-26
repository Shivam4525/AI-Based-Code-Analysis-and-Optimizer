import sys
import requests
import time

# Usage:
#   python test_api.py                          -> tests test_snippet.py as python
#   python test_api.py test_snippet_js.py javascript
#   python test_api.py test_snippet.py python

filename = sys.argv[1] if len(sys.argv) > 1 else "test_snippet.py"
language = sys.argv[2] if len(sys.argv) > 2 else "python"

with open(filename, "r", encoding="utf-8") as f:
    code = f.read()

print(f"Testing {filename} as {language}...")
start = time.time()

response = requests.post(
    "http://localhost:5000/api/analyze",
    json={"code": code, "language": language}
)

elapsed = time.time() - start
data = response.json()

print(f"Time taken: {elapsed:.1f} seconds")
print("Status code:", response.status_code)
print("Detected/used language:", data.get("language"))
print("Quality score:", data.get("quality_score"))
print("Total issues:", data.get("total_issues"))
print("---")
print("Issues:")
for issue in data.get("issues", []):
    print(f"  [{issue.get('severity')}] {issue.get('category')}: {issue.get('title')} (line {issue.get('line')})")
print("---")
print("verification_status:", data.get("verification_status"))
print("ai_error:", data.get("ai_error"))
print("resolved_issues:", data.get("resolved_issues"))
print("remaining_issues:", data.get("remaining_issues"))
print("new_issues:", data.get("new_issues"))
print("security_rejection_details:", data.get("security_rejection_details"))
print("---")
print("ai_explanation:", data.get("ai_explanation"))
print("---")
print("fixed_code:")
print(data.get("fixed_code"))
print("---")
print("risky_suggestions:", data.get("risky_suggestions"))