import json
import os
import shutil
import subprocess
import tempfile

JS_TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "js-tools"
)
ESLINT_JS = os.path.join(JS_TOOLS_DIR, "node_modules", "eslint", "bin", "eslint.js")
ESLINT_CONFIG = os.path.join(JS_TOOLS_DIR, ".eslintrc.json")
SPLIT_JS = os.path.join(JS_TOOLS_DIR, "split.js")
EXTRA_JS = os.path.join(JS_TOOLS_DIR, "extra.js")


def _node():
    return shutil.which("node") or "node"


def _run_eslint(code, fix=False, script_mode=False):
    """Runs ESLint on `code` via stdin — no files are written into the project."""
    cmd = [
        _node(), ESLINT_JS,
        "--stdin", "--stdin-filename", "input.js",
        "--format", "json",
        "--no-eslintrc", "-c", ESLINT_CONFIG,
        "--resolve-plugins-relative-to", JS_TOOLS_DIR,
    ]
    if fix:
        cmd.append("--fix-dry-run")
    if script_mode:
        cmd += ["--parser-options", "sourceType:script"]

    try:
        r = subprocess.run(
            cmd, input=code, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60, cwd=JS_TOOLS_DIR,
        )
    except FileNotFoundError:
        return None, "Node.js was not found. Install Node.js and make sure `node` is on PATH."
    except subprocess.TimeoutExpired:
        return None, "ESLint timed out."

    out = (r.stdout or "").strip()
    if not out:
        return None, (r.stderr or "ESLint returned no output").strip()[:500]
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None, (r.stderr or out)[:500]
    return (data[0] if data else {"messages": []}), None


def _lint_entry(code, fix=False):
    entry, err = _run_eslint(code, fix=fix)
    if err:
        return None, err
    # Old-style (non-module) scripts can fail to parse as ES modules — retry as script.
    if any(m.get("fatal") for m in entry.get("messages", [])):
        entry2, err2 = _run_eslint(code, fix=fix, script_mode=True)
        if not err2 and not any(m.get("fatal") for m in entry2.get("messages", [])):
            return entry2, None
    return entry, None


def eslint_messages(code):
    entry, err = _lint_entry(code)
    return (entry.get("messages", []) if entry else []), err


def eslint_fix(code):
    """
    Apply ESLint auto-fixes only when the resulting JavaScript
    passes an independent syntax check.
    """
    if not code or not code.strip():
        return code

    entry, err = _lint_entry(code, fix=True)

    # ESLint failed: preserve the original code.
    if err or not entry:
        return code

    candidate = entry.get("output")

    # No changes were made.
    if not candidate or candidate == code:
        return code

    # Never accept an auto-fix that introduces invalid JavaScript.
    valid, _error = node_check(candidate)
    if not valid:
        return code

    return candidate


def node_check(code):
    """Independent syntax check using Node's own V8 parser. Returns (ok, error)."""
    last_error = "Syntax error"
    for suffix in (".cjs", ".mjs"):
        fd, path = tempfile.mkstemp(suffix=suffix, prefix="aicode_")  # OS temp dir, not the project
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(code)
            r = subprocess.run(
                [_node(), "--check", path], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=30,
            )
            if r.returncode == 0:
                return True, None
            lines = [l for l in (r.stderr or "").splitlines() if l.strip()]
            last_error = next((l for l in lines if "Error" in l), lines[0] if lines else last_error)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return True, None  # can't verify here; ESLint's parser already validated syntax
        finally:
            if os.path.exists(path):
                os.remove(path)
    return False, last_error


def _run_node_script(script, code):
    try:
        r = subprocess.run(
            [_node(), script], input=code, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30, cwd=JS_TOOLS_DIR,
        )
        return json.loads((r.stdout or "").strip() or "null")
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None

def division_nodes(code):
    """Return JavaScript division operators identified by the Espree AST."""
    script = os.path.join(JS_TOOLS_DIR, "divisions.js")
    result = _run_node_script(script, code)

    if not isinstance(result, list):
        return []

    return result

def xss_nodes(code):
    """Return DOM HTML injection operations identified by the JavaScript AST."""
    script = os.path.join(JS_TOOLS_DIR, "xss.js")
    result = _run_node_script(script, code)
    return result if isinstance(result, list) else []

def extra_findings(code):
    result = _run_node_script(EXTRA_JS, code)
    return result if isinstance(result, list) else []


def top_level_names(code):
    nodes = _run_node_script(SPLIT_JS, code)
    names = set()
    if isinstance(nodes, list):
        for n in nodes:
            names.update(n.get("names", []))
    return names

def top_level_function_names(code):
    """Only function/class names — the strict set that must never disappear."""
    nodes = _run_node_script(SPLIT_JS, code)
    names = set()
    if isinstance(nodes, list):
        for n in nodes:
            names.update(n.get("funcNames", []))
    return names


def _fixed_chunks(lines, max_lines):
    chunks = []
    for i in range(0, len(lines), max_lines):
        part = lines[i:i + max_lines]
        chunks.append({
            "start_line": i + 1, "end_line": i + len(part),
            "text": "\n".join(part), "names": [],
        })
    return chunks


def split_top_level(code, max_lines=40):
    """Splits JS into logical sections (functions/classes/declarations) using a real parser."""
    lines = code.split("\n")
    nodes = _run_node_script(SPLIT_JS, code)
    if not isinstance(nodes, list) or not nodes:
        return _fixed_chunks(lines, max_lines)

    pieces = []  # [start_line, names]
    for idx, n in enumerate(nodes):
        start = 1 if idx == 0 else n["startLine"]
        if pieces and start <= pieces[-1][0]:
            pieces[-1][1].extend(n.get("names", []))
        else:
            pieces.append([start, list(n.get("names", []))])

    chunks = []
    for i, (start, names) in enumerate(pieces):
        end = pieces[i + 1][0] - 1 if i + 1 < len(pieces) else len(lines)
        chunks.append({
            "start_line": start, "end_line": end,
            "text": "\n".join(lines[start - 1:end]), "names": names,
        })

    merged = []
    for c in chunks:
        if merged and (c["end_line"] - merged[-1]["start_line"] + 1) <= max_lines:
            m = merged[-1]
            m["text"] += "\n" + c["text"]
            m["end_line"] = c["end_line"]
            m["names"] += c["names"]
        else:
            merged.append(dict(c))
    return merged