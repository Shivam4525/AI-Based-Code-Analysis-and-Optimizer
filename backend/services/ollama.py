
import ast
import re

import requests

from config import Config


class OllamaError(Exception):
    """Raised when an Ollama request or code generation fails."""
    pass


def _get_top_level_function_names(code: str) -> list:
    try:
        tree = ast.parse(code)
        return [
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        ]
    except SyntaxError:
        return []


def _call_ollama(prompt: str, num_predict: int = 1024) -> str:
    try:
        response = requests.post(
            f"{Config.OLLAMA_HOST}/api/generate",
            json={
                "model": Config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "30m",
                "options": {
                    "temperature": 0.1,
                    "num_predict": num_predict,
                },
            },
            timeout=Config.OLLAMA_TIMEOUT,
        )

        response.raise_for_status()
        data = response.json()

        return data.get("response", "")

    except requests.exceptions.ConnectionError as exc:
        raise OllamaError(
            "Could not connect to Ollama. Is it running? (ollama serve)"
        ) from exc

    except requests.exceptions.Timeout as exc:
        raise OllamaError("Ollama took too long to respond.") from exc

    except requests.exceptions.RequestException as exc:
        raise OllamaError(
            f"Ollama request failed: {str(exc)}"
        ) from exc



def _extract_code_block(text: str, language: str) -> str:
    """
    Extract code from a Markdown code block.
    Preserve code indentation and ensure a final newline.
    """
    text = text.strip()

    fence_pattern = re.compile(
        r"```(?:\w+)?[ \t]*\n(.*?)```",
        re.DOTALL,
    )

    match = fence_pattern.search(text)

    if match:
        code = match.group(1).strip("\r\n")
        return code + "\n" if code else ""

    # Handle a response with an opening fence but no closing fence.
    open_fence = re.search(
        r"```(?:\w+)?[ \t]*\n",
        text,
    )

    if open_fence:
        code = text[open_fence.end():].strip("\r\n")
        return code + "\n" if code else ""

    return text.rstrip("\r\n") + "\n" if text else ""



def _split_into_chunks(
    code: str,
    max_lines_per_chunk: int = 40,
) -> list:
    """
    Split Python code into chunks without dropping source lines.
    Prefer top-level AST boundaries; fall back to fixed-size chunks
    when the source cannot be parsed.
    """
    lines = code.splitlines(keepends=True)

    if not lines:
        return [code]

    if len(lines) <= max_lines_per_chunk:
        return [code]

    try:
        tree = ast.parse(code)
        nodes = [
            node for node in tree.body
            if hasattr(node, "lineno")
        ]

        if not nodes:
            return [
                "".join(lines[i:i + max_lines_per_chunk])
                for i in range(0, len(lines), max_lines_per_chunk)
            ]

        chunks = []
        start = 0

        for node in nodes:
            node_start = node.lineno - 1

            if node_start - start >= max_lines_per_chunk:
                chunks.append("".join(lines[start:node_start]))
                start = node_start

            node_end = getattr(node, "end_lineno", node.lineno)

            if node_end - start >= max_lines_per_chunk:
                chunks.append("".join(lines[start:node_end]))
                start = node_end

        if start < len(lines):
            chunks.append("".join(lines[start:]))

        return [chunk for chunk in chunks if chunk.strip()] or [code]

    except (SyntaxError, ValueError):
        return [
            "".join(lines[i:i + max_lines_per_chunk])
            for i in range(0, len(lines), max_lines_per_chunk)
        ]



def _issues_for_chunk(
    issues: list,
    chunk_start_line: int,
    chunk_end_line: int,
) -> list:
    return [
        issue
        for issue in issues
        if chunk_start_line
        <= issue.get("line", 0)
        <= chunk_end_line
    ]


def _fix_single_chunk(
    language: str,
    chunk_code: str,
    issues: list,
    other_function_names: list = None,
) -> str:
    issues_text = "\n".join(
        (
            f"- [{issue['severity']}] "
            f"{issue['title']}: {issue['description']}"
        )
        for issue in issues
    ) or (
        "No specific issues listed for this section. "
        "Only fix clear bugs if you find any."
    )

    context_note = ""

    if other_function_names:
        context_note = (
            "\nNote: this file also defines these functions "
            f"elsewhere: {', '.join(other_function_names)}. "
            "Do NOT redefine or duplicate them here."
        )

    prompt = f"""You are a senior {language} engineer.

Fix this {language} code section so it resolves these issues:
{issues_text}
{context_note}

CODE SECTION:
```{language}
{chunk_code}
```

Rules:
1. Preserve behavior, function names, and the public interface.
2. Fix listed issues and obvious bugs without rewriting unrelated logic.
3. Simplify only when it is safe to do so.
4. This is one section of a larger file. Do not add imports or
   code that belongs elsewhere.
5. Do not reference modules that were not imported or defined
   in this section unless they are available in the provided context.
6. For SQL injection, use parameterized queries with the correct
   database-driver placeholders. Never concatenate untrusted values
   into SQL statements.
7. Never use MD5 or plain SHA hashes for password storage. Use a
   suitable password-hashing function such as Argon2, scrypt, or bcrypt.
   Preserve existing password compatibility where required.
8. Never hardcode real passwords, API keys, or secrets. Use existing
   configuration or environment-variable mechanisms. Do not invent
   a new login flow or silently break authentication.
9. For try/except/pass findings:
   - Do not silently swallow failures that affect the operation.
   - Catch the narrowest appropriate exception type supported by
     the surrounding code; never invent an exception type.
   - If recovery is unsafe or unclear, let the exception propagate.
   - Use existing logging or error handling when available, without
     exposing passwords, SQL parameters, or other sensitive data.
   - Preserve transaction and resource-cleanup behavior.
   - Never report a failed database write as successful.
   - Do not add an empty pass, suppress the scanner, or claim the
     finding is fixed unless the resulting code actually fixes it.
10. Do not duplicate imports or functions that belong elsewhere in the
    file. If a safe fix requires changes outside this section, preserve
    the section and do not pretend the issue has been fixed.
11. Fix the actual root cause of each security issue; do not merely
    suppress warnings or change the code to evade the scanner.

Respond with ONLY the corrected code inside one {language}
code block. Do not include explanations or commentary.
"""

    raw = _call_ollama(prompt, num_predict=1200)

    return _extract_code_block(raw, language)


def get_fixed_code(
    language: str,
    code: str,
    issues: list,
) -> str:
    code_lines = code.count("\n") + 1

    def _single_shot_fix(max_tokens: int) -> str:
        severity_order = {
            "Critical": 0,
            "High": 1,
            "Medium": 2,
            "Low": 3,
        }

        top_issues = sorted(
            issues,
            key=lambda issue: severity_order.get(
                issue.get("severity"),
                4,
            ),
        )

        issues_text = "\n".join(
            (
                f"- [{issue['severity']}] {issue['title']} "
                f"(line {issue['line']}): {issue['description']}"
            )
            for issue in top_issues
        ) or (
            "No specific issues listed. Review the code for "
            "bugs, security, and performance problems."
        )

        prompt = f"""You are a senior {language} engineer
performing a code review and refactor.

Fix the following {language} code so it resolves these issues:
{issues_text}

ORIGINAL CODE:
```{language}
{code}
```

  Rules:
  1. Preserve the intended behavior, inputs, outputs, and public names
     wherever reasonable.
  2. Fix the listed issues at their root cause, not merely by hiding
     warnings or changing their wording.
  3. Treat Critical and High security findings as mandatory fixes.
  4. Avoid shell execution for user-controlled input. Do not use
     shell=True when a safer alternative is practical.
  5. Prefer simpler standard-library solutions when they preserve
     the intended behavior. For example, use print() instead of
     subprocess when the program only needs to display text.
  6. Never remove necessary validation or weaken security controls
     just to make a scanner report fewer findings.
  7. Never reference a class, function, or module that is not
     defined or imported in the available code.
  8. Simplify only when behavior is preserved.
  9. Keep the code idiomatic, readable, and maintainable.
  10. Do not claim that tests passed unless tests were actually run.
  11. Return complete corrected code, not a partial snippet.
  12. If a security issue cannot be safely fixed without knowing
      the intended behavior, preserve the code and avoid inventing
      a potentially unsafe replacement.
  13. For SQL injection, use parameterized queries with database-driver
      placeholders. Never concatenate untrusted values into SQL.
  14. Never use MD5 or plain SHA hashes for password storage. Use an
      appropriate password-hashing function such as Argon2, scrypt, or
      bcrypt, while considering compatibility with existing passwords.
  15. Do not hardcode real passwords, API keys, or secrets. Use
      configuration or environment variables and handle missing values safely.
  16. When a finding identifies try/except/pass or a bare except:
      - Replace the bare except with the narrowest appropriate exception
        type supported by the surrounding code.
      - Do not use an empty pass body to silently discard an operation
        failure when that failure affects the requested operation.
      - Handle the failure meaningfully: use the project's existing
        logging/error-reporting mechanism if present, or re-raise the
        exception when safe recovery is not possible.
      - Do not expose credentials, SQL parameters, or other secrets in
        error messages.
      - Preserve resource cleanup and close database cursors/connections
        appropriately; do not invent rollback or retry behavior without
        considering transaction semantics.
      - If the required behavior is unclear, do not fabricate success.
  17. For database writes, use parameterized queries and preserve commit
      behavior. On failure, do not report success; propagate or handle
      the error explicitly.
  18. Fix the root cause of each security finding. Do not claim an issue
      is fixed unless the resulting code actually addresses it.

Respond with ONLY the corrected code inside one {language}
code block. No explanation or commentary.
"""

        last_error = None

        for attempt in range(2):
            try:
                raw = _call_ollama(
                    prompt if attempt == 0 else (
                        prompt
                        + "\n\nIMPORTANT: Your previous response was "
                        "empty or incomplete. Return the COMPLETE corrected "
                        "source code in one code block. Do not omit any "
                        "required functions or sections."
                    ),
                    num_predict=max_tokens,
                )

                candidate = _extract_code_block(raw, language)

                if candidate.strip():
                    from services.validation import validate_fixed_code

                    validation = validate_fixed_code(
                        language,
                        candidate,
                        code,
                    )

                    if validation.get("valid"):
                        return validation.get("code", candidate)

                    last_error = (
                        validation.get("error")
                        or "Generated code failed validation."
                    )

                    if attempt == 0:
                        prompt += (
                            "\n\nYour previous candidate failed validation: "
                            + str(last_error)
                            + "\nReturn a complete corrected version that "
                            "fixes this validation error."
                        )
                    else:
                         last_error = "Ollama returned empty code."

            except OllamaError as exc:
                last_error = str(exc)
                if attempt == 1:
                    raise

        raise OllamaError(
            last_error or "Ollama failed to generate corrected code."
        )

    # Small files and non-Python files use a single Ollama call.
    if code_lines <= 50 or language.lower() != "python":
        num_predict = 1024 if code_lines <= 40 else 2048

        return _single_shot_fix(num_predict)

    # Larger Python files: try chunking first.
    chunks = _split_into_chunks(
        code,
        max_lines_per_chunk=40,
    )

    all_function_names = _get_top_level_function_names(code)
    fixed_chunks = []
    line_cursor = 1

    for chunk in chunks:
        chunk_line_count = chunk.count("\n") + 1

        chunk_issues = _issues_for_chunk(
            issues,
            line_cursor,
            line_cursor + chunk_line_count,
        )

        chunk_function_names = _get_top_level_function_names(
            chunk
        )

        other_names = [
            name
            for name in all_function_names
            if name not in chunk_function_names
        ]

        try:
            fixed = _fix_single_chunk(
                language,
                chunk,
                chunk_issues,
                other_function_names=other_names,
            )

            fixed_chunks.append(
                fixed if fixed.strip() else chunk
            )

        except OllamaError:
            # Preserve the original chunk if generation fails.
            fixed_chunks.append(chunk)

        line_cursor += chunk_line_count

    chunked_result = "\n\n".join(fixed_chunks)

    # Validate the merged result before accepting it.
    from services.validation import check_for_chunking_artifacts

    try:
        ast.parse(chunked_result)

        artifact_error = check_for_chunking_artifacts(
            code,
            chunked_result,
        )

    except SyntaxError:
        artifact_error = "Syntax error in merged code"

    if artifact_error:
        # Retry with the full code in one request.
        return _single_shot_fix(3072)

    from services.validation import validate_fixed_code

    validation = validate_fixed_code(
        language,
        chunked_result,
        code,
    )

    if validation.get("valid"):
        return validation.get("code", chunked_result)

    # If merged chunks fail validation, retry using the full source.
    return _single_shot_fix(3072)


def get_explanation(language: str, issues: list) -> str:
    """
    Build a concise explanation directly from detected issues.
    This avoids inventing issue names or line numbers.
    """
    if not issues:
        return (
            f"The analysis did not detect any issues "
            f"in the provided {language} code."
        )

    severity_order = {
        "Critical": 0,
        "High": 1,
        "Medium": 2,
        "Low": 3,
    }

    ordered_issues = sorted(
        issues,
        key=lambda issue: severity_order.get(
            issue.get("severity", ""),
            4,
        ),
    )

    highest = ordered_issues[0]

    title = str(
        highest.get("title") or "An issue was detected"
    ).strip()

    severity = str(
        highest.get("severity") or "Unknown"
    )

    line = highest.get("line")
    total = len(issues)

    line_text = (
        f" on line {line}"
        if line is not None
        else ""
    )

    summary = (
        f"The analysis detected {total} issue"
        f"{'s' if total != 1 else ''}. "
        f"The highest-priority finding is '{title}'"
        f"{line_text} ({severity} severity)."
    )

    if total > 1:
        summary += (
            " Review the remaining findings and their "
            "recommendations to address the other detected issues."
        )
    else:
        summary += (
            " Review the recommendation to address this issue."
        )

    return summary


def generate_explanation_and_fix(
    language: str,
    code: str,
    issues: list,
) -> dict:
    """
    Generate corrected code and a deterministic issue summary.
    """
    fixed_code = get_fixed_code(
        language,
        code,
        issues,
    )

    explanation = get_explanation(
        language,
        issues,
    )

    if not fixed_code or not fixed_code.strip():
        raise OllamaError(
            "Ollama did not return any fixed code."
        )

    return {
        "explanation": explanation,
        "fixed_code": fixed_code,
    }
