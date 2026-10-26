import re

from analyzers.javascript_analyzer import JavaScriptAnalyzer
from services import js_tools
from services.scoring import SEVERITY_WEIGHTS
from services.ollama import _call_ollama, _extract_code_block, OllamaError

RISKY_RULES = ("eval", "new function")

CHUNK_THRESHOLD_LINES = 150      # longer files are fixed section by section
CHUNK_SIZE_LINES = 40
MAX_ATTEMPTS = 2                 # per section: first try + retries with feedback
SKIP_LOW_ONLY_SECTIONS = True    # don't spend AI time on purely cosmetic sections

_analyzer = JavaScriptAnalyzer()
_UNDEFINED = re.compile(r"'([^']+)' is not defined")


def _analyze(code):
    return _analyzer.safe_analyze(code)


def _tool_failed(issues):
    return any(i["title"].startswith("ESLint could not run") for i in issues)


def _undefined_names(issues):
    names = set()
    for i in issues:
        m = _UNDEFINED.search(i["title"])
        if m:
            names.add(m.group(1))
    return names


def _severe_count(issues):
    return sum(1 for i in issues if i["severity"] in ("Critical", "High"))


def _penalty(issues):
    """Uncapped weight of all issues (the 0-100 score floors at 0 and can't show progress)."""
    return sum(SEVERITY_WEIGHTS.get(i["severity"], 0) for i in issues)


def _format_issues(issues, limit=10):
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    top = sorted(issues, key=lambda i: order.get(i["severity"], 4))[:limit]
    return "\n".join(
        f"- [{i['severity']}] {i['title']} (line {i['line']})" for i in top
    ) or "- No specific issues listed; review for bugs and security problems."


def _build_prompt(section, issues, other_names=None, feedback=None, is_section=False):
    context = ""
    if is_section:
        context += "\nThis is ONE SECTION of a larger file. Do not add imports that belong elsewhere."
        if other_names:
            context += f"\nThese are defined elsewhere in the file — do NOT redefine them: {', '.join(other_names)}."
    if feedback:
        context += f"\nYour previous attempt was rejected because {feedback}. Avoid that mistake this time."

    return f"""You are a senior JavaScript engineer doing a careful code review and refactor.

Fix this JavaScript code so it resolves these issues:
{_format_issues(issues)}
{context}

CODE:
```javascript
{section}
```

Rules:
1. Preserve the original program's behavior and all public function names.
   Fix duplicate declarations carefully. If the same variable is declared
   with var multiple times in the same function or script, do not convert
   every declaration into let or const. Declare it once and use assignment
   for later updates. Use const only when the variable is never reassigned.
   Never introduce duplicate let or const declarations in the same scope.
2. Fix EVERY listed issue — do not skip any, especially Critical and High severity ones.
3. NEVER invent modules, imports, classes or globals. If an identifier is used but never defined (for example db), do not create it out of thin air: accept it as a function parameter or leave a short TODO comment.
4. Security — fix ALL of these that appear, do not skip any:
   - eval(x) / new Function(x): replace it with a direct call. If x looks like a function name or expression, call it directly (e.g. eval(fn) becomes fn()). If x represents JSON/data, use JSON.parse(x). If the exact intent is unclear, call the most reasonable direct equivalent — never leave eval or new Function in the output.
   - SQL built with string concatenation: use placeholders and a separate values array.
   - hardcoded secrets/keys: move them to process.env.NAME.
   - md5/sha1 hashing: replace with sha256 or better.
   - innerHTML/document.write with dynamic data: use textContent instead.
5. Simplify only where behavior is provably unchanged (var to const/let, === instead of ==, Set/Map instead of repeated array scans, removing dead code).
6. Keep the module system of the original (require stays require, import stays import).

Respond with ONLY the corrected code inside a single javascript code block:
```javascript
<corrected code here>
```
No explanation, no commentary.
"""


def _generate(section, issues, other_names, feedback, is_section):
    lines = section.count("\n") + 1
    budget = min(3072, max(1024, lines * 40))   # scale output budget to section size
    raw = _call_ollama(
        _build_prompt(section, issues, other_names, feedback, is_section),
        num_predict=budget,
    )
    return _extract_code_block(raw, "javascript").strip("\n")

def _repair_duplicate_let_declaration(code, error):
    """Repair a repeated same-indent let declaration after a syntax error."""
    match = re.search(
        r"Identifier '([^']+)' has already been declared",
        error or "",
    )
    if not match:
        return code

    name = match.group(1)
    pattern = re.compile(
        r"^(?P<indent>[ \t]*)let\s+"
        + re.escape(name)
        + r"\s*=",
        re.MULTILINE,
    )

    matches = list(pattern.finditer(code))
    if len(matches) < 2:
        return code

    # Only repair repeated declarations at the same indentation.
    first_indent = matches[0].group("indent")
    lines = code.splitlines()
    seen = False
    changed = False

    for index, line in enumerate(lines):
        m = pattern.match(line)
        if not m or m.group("indent") != first_indent:
            continue

        if not seen:
            seen = True
            continue

        prefix_end = m.start() + len(m.group("indent"))
        lines[index] = (
            line[:prefix_end]
            + line[prefix_end:].replace("let ", "", 1)
        )
        changed = True

    if not changed:
        return code

    repaired = "\n".join(lines)

    # Never use the repair unless Node confirms valid syntax.
    valid, _ = js_tools.node_check(repaired)
    return repaired if valid else code

def _check_section(original, candidate):
    """Cheap local checks on one section. Returns (status, reason)."""
    if not candidate.strip() or candidate.strip() == original.strip():
        return "unchanged", None

    ok, err = js_tools.node_check(candidate)
 
    if not ok:
        print("[JS FIX DEBUG] Candidate rejected:", err)
        print("[JS FIX DEBUG] Generated candidate:\n", candidate)
        return "reject", f"it has a syntax error ({err})"

    if len(candidate) < 0.4 * len(original):
        return "reject", "it dropped too much of the original code"

    missing = js_tools.top_level_function_names(original) - js_tools.top_level_function_names(candidate)
    if missing:
        return "reject", f"it removed or renamed these functions/classes: {', '.join(sorted(missing))}"

    if "await" in candidate and "await" in original:
        # crude but effective: every await must still be inside an async function
        for m in re.finditer(r"\bawait\b", candidate):
            before = candidate[:m.start()]
            if "async function" not in before and "async (" not in before and "async " not in before[-200:]:
                return "reject", "it kept an await but removed the surrounding async function"

    return "ok", None


def _evaluate(base_issues, candidate_file):
    """Whole-file verification of a candidate (with one section replaced)."""
    cand_issues = _analyze(candidate_file)
    if _tool_failed(cand_issues):
        return {"accepted": False, "reason": None, "issues": None}

    new_undefined = _undefined_names(cand_issues) - _undefined_names(base_issues)
    if new_undefined:
        return {"accepted": False, "issues": None,
                "reason": f"it introduced undefined identifiers: {', '.join(sorted(new_undefined))}"}

    # Automatable Critical issues must be fixed; eval/new Function get one
    # pass here but are handled by the fast, focused snippet-fixer afterward
    # if this whole-file attempt doesn't resolve them — no point retrying
    # the whole file 3 times just for those.
    base_critical_titles = {i["title"] for i in base_issues if i["severity"] == "Critical"}
    cand_critical_titles = {i["title"] for i in cand_issues if i["severity"] == "Critical"}
    unfixed_critical = base_critical_titles & cand_critical_titles
    unfixed_non_risky = {t for t in unfixed_critical if not any(r in t.lower() for r in RISKY_RULES)}
    if unfixed_non_risky:
        return {"accepted": False, "issues": None,
                "reason": f"it left this Critical issue unfixed: {', '.join(sorted(unfixed_non_risky))}"}

    if _severe_count(cand_issues) > _severe_count(base_issues):
        return {"accepted": False, "issues": None,
                "reason": "it introduced more serious issues than it fixed"}

    if _penalty(cand_issues) >= _penalty(base_issues):
        return {"accepted": False, "issues": None,
                "reason": "it did not resolve any of the listed issues"}

    return {"accepted": True, "reason": None, "issues": cand_issues}


def _improve_section(parts, idx, base_issues, sec_issues, others, is_section):
    """Returns (new_section_text, new_file_issues, rejection_reason)."""
    feedback = None
    for _ in range(MAX_ATTEMPTS):
        try:
            cand = _generate(parts[idx], sec_issues, others, feedback, is_section)
        except OllamaError as e:
            return None, None, f"AI unavailable ({e})"

        # Do not run ESLint auto-fixes on AI output here.
        # They may convert repeated `var` declarations into duplicate `let`
        # declarations and make otherwise valid JavaScript invalid.
        cand = cand.strip()

        valid, syntax_error = js_tools.node_check(cand)
        if not valid:
            cand = _repair_duplicate_let_declaration(cand, syntax_error)

        status, reason = _check_section(parts[idx], cand)
        if status == "unchanged":
            return None, None, "the model proposed no change"
        if status == "reject":
            feedback = reason
            continue

        trial = "\n".join(parts[:idx] + [cand] + parts[idx + 1:])
        ok, err = js_tools.node_check(trial)
        if not ok:
            feedback = f"the combined file has a syntax error ({err})"
            continue

        verdict = _evaluate(base_issues, trial)
        if verdict["accepted"]:
            return cand, verdict["issues"], None
        feedback = verdict["reason"]
        if not feedback:
            break

    return None, None, feedback or "verification failed"


def fix_javascript(code, issues):
    """
    Returns (final_code, notes, fixed_count). final_code is ALWAYS
    syntactically valid: verified AI improvements (including eval /
    new Function replacements) are applied section by section; anything
    that fails verification after all retries stays as the safe
    pre-AI version — same guarantee as the Python pipeline.
    """
    notes = []

    if not code.strip():
        return code, notes, 0

    # Stage 1 — mechanical, deterministic fixes (no AI involved)
    pre = js_tools.eslint_fix(code)
    if pre != code:
        ok, _ = js_tools.node_check(pre)
        if ok:
            notes.append("Safe ESLint auto-fixes were applied (var to let/const, prefer-const, etc.).")
        else:
            pre = code

    # Stage 2 — re-analyze so line numbers and remaining issues are accurate
    current_issues = _analyze(pre)
    if _tool_failed(current_issues) or not current_issues:
        return pre, notes, 0

    # Stage 3 — decide the sections
    is_section = (pre.count("\n") + 1) > CHUNK_THRESHOLD_LINES
    if is_section:
        chunks = js_tools.split_top_level(pre, CHUNK_SIZE_LINES)
        parts = [c["text"] for c in chunks]
        section_names = [c["names"] for c in chunks]
    else:
        parts = [pre]
        section_names = [[]]

    improved, cosmetic_skipped, rejected, fixed_count = 0, 0, [], 0

    # Stage 4 — improve each section, verifying each one before keeping it
    for idx in range(len(parts)):
        start = 1 + sum(p.count("\n") + 1 for p in parts[:idx])
        end = start + parts[idx].count("\n")
        sec_issues = (
            [i for i in current_issues if start <= i["line"] <= end]
            if is_section else current_issues
        )
        if not sec_issues:
            continue
        if is_section and SKIP_LOW_ONLY_SECTIONS and all(i["severity"] == "Low" for i in sec_issues):
            cosmetic_skipped += 1
            continue

        others = (
            [n for j, ns in enumerate(section_names) if j != idx for n in ns]
            if is_section else []
        )
        before_count = len(sec_issues)
        cand, new_issues, why = _improve_section(parts, idx, current_issues, sec_issues, others, is_section)
        if cand is not None:
            parts[idx] = cand
            after_count = len([i for i in new_issues if start <= i["line"] <= end]) if is_section else len(new_issues)
            fixed_count += max(0, before_count - after_count)
            current_issues = new_issues
            improved += 1
        else:
            rejected.append((start, end, why))

    if improved:
        notes.append(
            f"AI fixes passed verification and were applied to {improved} section(s)."
            if is_section else "The AI fix passed verification (valid syntax, no new undefined names, fewer issues)."
        )
    for s, e, why in rejected[:3]:
        where = f"Lines {s}-{e}" if is_section else "One part of the code"
        notes.append(f"{where} could not be safely auto-fixed ({why}).")
    if cosmetic_skipped:
        notes.append(f"{cosmetic_skipped} section(s) with only cosmetic issues were left unchanged.")

    return "\n".join(parts), notes, fixed_count


def _suggest_risky_fix(code, issue):
    """
    For patterns that stayed unresolved after the normal pipeline (most
    often eval/new Function when every retry was rejected), generate one
    more focused, clearly-labeled suggested replacement — same workflow
    Snyk/SonarQube use for their "suggested fix" feature.
    """
    lines = code.split("\n")
    start = max(1, issue["line"] - 2)
    end = min(len(lines), issue["line"] + 2)
    snippet = "\n".join(lines[start - 1:end])

    prompt = f"""You are a senior JavaScript security engineer.

This code snippet has the issue: {issue['title']}

SNIPPET (line {issue['line']} is the problem line):
```javascript
{snippet}
```

Show ONLY the corrected version of this snippet, replacing the risky pattern with the safest direct equivalent.
If the exact intent is ambiguous, pick the most common safe pattern and add a one-line comment explaining the assumption.

Respond with ONLY the corrected snippet inside a code block:
```javascript
<corrected snippet>
```
No explanation outside the code block.
"""
    try:
        raw = _call_ollama(prompt, num_predict=400)
        suggestion = _extract_code_block(raw, "javascript").strip()
        return suggestion or None
    except OllamaError:
        return None


def get_unresolved_risky_issues(original_code, final_code, issues):
    """
    Returns risky-pattern issues (eval/new Function) that are STILL present
    in final_code after the normal fix pipeline ran — so we only generate
    an extra suggestion for what genuinely wasn't resolved.
    """
    still_present = _analyze(final_code)
    still_titles = {i["title"] for i in still_present}
    return [
        i for i in issues
        if any(r in i["title"].lower() for r in RISKY_RULES) and i["title"] in still_titles
    ]


def get_risky_suggestions(original_code, final_code, issues):
    unresolved = get_unresolved_risky_issues(original_code, final_code, issues)
    results = []
    for issue in unresolved:
        suggestion = _suggest_risky_fix(final_code, issue)
        results.append({
            "title": issue["title"],
            "line": issue["line"],
            "suggestion": suggestion or "(Could not generate a suggestion automatically — please review this line.)",
        })
    return results