def extract_snippet(code: str, line_number: int, context: int = 2) -> str:
    """
    Returns a few lines of code around the given line number,
    with line numbers prefixed — e.g.:
        21  def connect():
        22      username = "admin"
    23      password = "admin123"
        24      db = connect(...)

    context = how many lines to show before/after the target line.
    """
    if not code or not line_number or line_number < 1:
        return ""

    lines = code.split("\n")
    total = len(lines)

    # line_number is 1-indexed; clamp the window to valid bounds
    start = max(1, line_number - context)
    end = min(total, line_number + context)

    snippet_lines = []
    for i in range(start, end + 1):
        prefix = ">>" if i == line_number else "  "
        snippet_lines.append(f"{prefix} {i:>3}  {lines[i - 1]}")

    return "\n".join(snippet_lines)