import ast
import re
import subprocess
import sys
import tempfile
import os as _os
import json as _json


def _has_undefined_variables(code: str) -> list:
    """
    Uses pylint's own undefined-variable check (E0602) on the given code —
    far more reliable than any hand-written heuristic, since it actually
    resolves scopes/imports/definitions the way Python would. Returns a
    list of undefined names found (empty if none).
    """
    path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".py", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            path = f.name

        result = subprocess.run(
            [sys.executable, "-m", "pylint", path,
             "--disable=all", "--enable=undefined-variable",
             "--output-format=json"],
            capture_output=True, text=True, timeout=30,
        )

        if not result.stdout.strip():
            return []

        raw = _json.loads(result.stdout)
        return [r["message"] for r in raw if r.get("symbol") == "undefined-variable"]

    except (subprocess.TimeoutExpired, _json.JSONDecodeError, FileNotFoundError):
        return []
    finally:
        if path and _os.path.exists(path):
            _os.remove(path)


def _try_parse(code: str):
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)


def _escape_raw_newlines_inside_strings(code: str) -> str:
    """
    Fixes the case where a raw newline character ended up INSIDE a single-line
    quoted string (e.g. print("
SHIVAM")) instead of the intended two-character
    escape sequence \\n. Walks the code tracking whether we're inside a quote,
    and converts any literal newline found there back into the text \n.
    Newlines OUTSIDE strings (real line breaks between statements) are left
    untouched.
    """
    result = []
    in_string = False
    quote_char = None
    escape_next = False

    for ch in code:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue

        if ch == "\\":
            result.append(ch)
            escape_next = True
            continue

        if in_string:
            if ch == quote_char:
                in_string = False
                quote_char = None
                result.append(ch)
                continue
            if ch == "\n":
                result.append("\\n")  # put back the 2-char escape sequence
                continue
            if ch == "\t":
                result.append("\\t")
                continue
            result.append(ch)
            continue

        # not currently inside a string
        if ch in ('"', "'"):
            in_string = True
            quote_char = ch
            result.append(ch)
            continue

        result.append(ch)

    return "".join(result)


def validate_fixed_code(
    language: str,
    fixed_code: str,
    original_code: str = "",
) -> dict:
    """
    Strict validation for AI-generated code.

    A successful result means the code passed the checks implemented
    here. It does not guarantee functional correctness or security.
    """

    if not isinstance(fixed_code, str) or not fixed_code.strip():
        return {
            "valid": False,
            "error": "AI returned empty or invalid code.",
            "code": fixed_code if isinstance(fixed_code, str) else "",
            "verification_status": "rejected",
            "checks": {"non_empty": False},
        }

    checks = {
        "non_empty": True,
        "syntax": None,
        "duplicate_functions": None,
        "undefined_names": None,
    }

    # Python syntax validation
    if language == "python":
        try:
            ast.parse(fixed_code)
            checks["syntax"] = True
        except SyntaxError as exc:
            return {
                "valid": False,
                "error": (
                    f"AI-generated Python has a syntax error "
                    f"at line {exc.lineno}: {exc.msg}"
                ),
                "code": fixed_code,
                "verification_status": "rejected",
                "checks": {**checks, "syntax": False},
            }

        # Check duplicate top-level functions and undefined names.
        artifact_error = check_for_chunking_artifacts(
            original_code,
            fixed_code,
        )

        if artifact_error:
            return {
                "valid": False,
                "error": artifact_error,
                "code": fixed_code,
                "verification_status": "rejected",
                "checks": {
                    **checks,
                    "syntax": True,
                    "duplicate_functions": (
                        not artifact_error.startswith(
                            "Duplicate function definitions"
                        )
                    ),
                    "undefined_names": (
                        not artifact_error.startswith(
                            "Fixed code references undefined names"
                        )
                    ),
                },
            }

        checks["duplicate_functions"] = True
        checks["undefined_names"] = True

        return {
            "valid": True,
            "error": None,
            "code": fixed_code,
            "verification_status": "syntax_and_static_checks_passed",
            "checks": checks,
        }

    # JavaScript must be validated with the Node.js checker.
    if language == "javascript":
        try:
            from services import js_tools

            syntax_valid, syntax_error = js_tools.node_check(fixed_code)
        except Exception:
            return {
                "valid": None,
                "error": "JavaScript validator could not run.",
                "code": fixed_code,
                "verification_status": "unverified",
                "checks": checks,
            }

        checks["syntax"] = bool(syntax_valid)

        if not syntax_valid:
            return {
                "valid": False,
                "error": f"JavaScript syntax validation failed: {syntax_error}",
                "code": fixed_code,
                "verification_status": "rejected",
                "checks": checks,
            }

        return {
            "valid": True,
            "error": None,
            "code": fixed_code,
            "verification_status": "syntax_checked",
            "checks": checks,
        }

    # Do not claim validation for unsupported languages.
    return {
        "valid": None,
        "error": (
            f"Automated validation is not implemented for "
            f"'{language}'. The generated code is unverified."
        ),
        "code": fixed_code,
        "verification_status": "unverified",
        "checks": checks,
    }



def _get_top_level_function_names(code: str) -> list:
    try:
        tree = ast.parse(code)
        return [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    except SyntaxError:
        return []


def _get_undefined_names(code: str) -> list:
    """
    Narrow, targeted check: only flags module-like names used specifically
    inside `except ModuleName.SomeError` clauses where ModuleName was never
    imported anywhere in the file. This catches AI hallucinated imports
    (e.g. `except psycopg2.DatabaseError`) without flagging normal local
    variable method calls like `cursor.execute()` or `matches.append()`.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    suspicious = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is not None:
            # node.type can be a single expression or a Tuple of expressions
            type_exprs = node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]
            for expr in type_exprs:
                if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name):
                    module_name = expr.value.id
                    if module_name not in imported:
                        suspicious.add(module_name)

    return list(suspicious)


def check_for_chunking_artifacts(original_code: str, fixed_code: str) -> str | None:
    fixed_funcs = _get_top_level_function_names(fixed_code)
    duplicates = {f for f in fixed_funcs if fixed_funcs.count(f) > 1}
    if duplicates:
        return f"Duplicate function definitions found after merging: {', '.join(duplicates)}"

    undefined = _has_undefined_variables(fixed_code)
    if undefined:
        return f"Fixed code references undefined names: {'; '.join(undefined[:3])}"

    return None

def _remove_duplicate_functions(code: str) -> str:
    """
    If a function is defined more than once at top level, keep only the
    LAST definition (chunking usually refines earlier ones) and remove
    the earlier duplicate(s) entirely.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    lines = code.split("\n")
    func_ranges = {}  # name -> list of (start_line, end_line) 0-indexed

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            start = node.lineno - 1
            end = getattr(node, "end_lineno", node.lineno)
            func_ranges.setdefault(node.name, []).append((start, end))

    # Find which line ranges to delete: all but the LAST occurrence of each duplicated name
    ranges_to_delete = []
    for name, ranges in func_ranges.items():
        if len(ranges) > 1:
            ranges_to_delete.extend(ranges[:-1])  # keep only the last

    if not ranges_to_delete:
        return code

    # Delete those line ranges (process in reverse so indices don't shift)
    ranges_to_delete.sort(key=lambda r: r[0], reverse=True)
    for start, end in ranges_to_delete:
        del lines[start:end]

    return "\n".join(lines)


def _remove_undefined_attribute_refs(code: str, undefined_names: list) -> str:
    """
    Replaces bare `except (SomeUndefinedModule.Error, ...)` patterns by
    dropping the undefined part, falling back to `except Exception as e:`
    for that clause if needed. This is a targeted fix for the common
    hallucinated-import case, not a general code rewriter.
    """
    import re
    result = code
    for name in undefined_names:
        # Pattern: except (Exception, name.SomeError) as e:  ->  except Exception as e:
        pattern = re.compile(
            rf'except\s*\(\s*([^,()]+),\s*{re.escape(name)}\.\w+\s*\)\s*as\s+(\w+)\s*:'
        )
        result = pattern.sub(r'except \1 as \2:', result)
        # Pattern: except name.SomeError as e:  ->  except Exception as e:
        pattern2 = re.compile(rf'except\s+{re.escape(name)}\.\w+\s+as\s+(\w+)\s*:')
        result = pattern2.sub(r'except Exception as \1:', result)
    return result