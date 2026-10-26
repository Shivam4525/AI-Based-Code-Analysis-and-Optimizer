
import re
from services import js_tools


def _mask_comments_and_strings(code):
    """Mask comments and string text while preserving template expressions."""
    result = list(code)
    n = len(code)

    def blank(pos):
        if code[pos] != "\n":
            result[pos] = " "

    def scan_string(pos, quote):
        # pos points at the opening quote.
        blank(pos)
        pos += 1

        while pos < n:
            ch = code[pos]

            if ch == "\\":
                blank(pos)
                if pos + 1 < n:
                    blank(pos + 1)
                pos += 2
                continue

            blank(pos)
            pos += 1

            if ch == quote:
                break

        return pos

    def scan_template(pos):
        # pos points just after the opening backtick.
        while pos < n:
            ch = code[pos]

            if ch == "\\":
                blank(pos)
                if pos + 1 < n:
                    blank(pos + 1)
                pos += 2
                continue

            if ch == "`":
                blank(pos)
                return pos + 1

            if ch == "$" and pos + 1 < n and code[pos + 1] == "{":
                blank(pos)
                blank(pos + 1)
                pos = scan_code(pos + 2, stop_at_brace=True)
                continue

            blank(pos)
            pos += 1

        return pos

    def scan_code(pos, stop_at_brace=False):
        brace_depth = 0

        while pos < n:
            ch = code[pos]
            nxt = code[pos + 1] if pos + 1 < n else ""

            if stop_at_brace and ch == "}":
                if brace_depth == 0:
                    return pos + 1
                brace_depth -= 1
                pos += 1
                continue

            if ch == "{":
                brace_depth += 1
                pos += 1
                continue

            if ch == "/" and nxt == "/":
                blank(pos)
                blank(pos + 1)
                pos += 2

                while pos < n and code[pos] != "\n":
                    blank(pos)
                    pos += 1

                continue

            if ch == "/" and nxt == "*":
                blank(pos)
                blank(pos + 1)
                pos += 2

                while pos < n:
                    if (
                        code[pos] == "*"
                        and pos + 1 < n
                        and code[pos + 1] == "/"
                    ):
                        blank(pos)
                        blank(pos + 1)
                        pos += 2
                        break

                    blank(pos)
                    pos += 1

                continue

            if ch in ("'", '"'):
                pos = scan_string(pos, ch)
                continue

            if ch == "`":
                blank(pos)
                pos = scan_template(pos + 1)
                continue

            pos += 1

        return pos

    scan_code(0)
    return "".join(result)


def find_division_by_zero_risks(code):
    """
    Detect literal-zero divisors and simple known-zero variables.

    Espree AST identifies actual JavaScript division operators, avoiding
    false positives from regex literals, comments, and ordinary strings.
    Variable tracking is conservative and does not fully model scopes
    or control flow.
    """
    issues = []
    masked_code = _mask_comments_and_strings(code)
    lines = masked_code.splitlines()

    # Get actual division operators from the JavaScript AST.
    division_nodes = js_tools.division_nodes(code)

    if not isinstance(division_nodes, list):
        division_nodes = []

    divisions_by_line = {}

    for node in division_nodes:
        if not isinstance(node, dict):
            continue

        line_number = node.get("line")

        if isinstance(line_number, int) and line_number > 0:
            divisions_by_line.setdefault(line_number, []).append(node)

    zero_assignment = re.compile(
        r"^\s*(?:(?:const|let|var)\s+)?"
        r"([A-Za-z_$][\w$]*)\s*=\s*(.*?)\s*;?\s*$"
    )

    zero_value = re.compile(r"^(?:0+(?:\.0*)?|\.0+)$")

    # Track simple assignments encountered before each division.
    zero_variables = set()

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        line_divisions = divisions_by_line.get(line_number, [])

        for node in line_divisions:
            right_type = node.get("rightType")
            right_value = node.get("rightValue")

            # Case 1: Direct division by a numeric literal zero.
            if (
                right_type == "Literal"
                and isinstance(right_value, (int, float))
                and not isinstance(right_value, bool)
                and right_value == 0
            ):
                issues.append({
                    "category": "bug",
                    "severity": "High",
                    "line": line_number,
                    "title": "Division by zero",
                    "description": (
                        "The expression divides by a literal numeric zero. "
                        "JavaScript numeric division may produce Infinity or NaN."
                    ),
                    "recommendation": (
                        "Validate the divisor before dividing, and handle zero "
                        "explicitly when it is not a valid input."
                    ),
                })
                break

            # Case 2: Division by a variable previously assigned zero.
            variable = node.get("rightName")

            if variable and variable in zero_variables:
                issues.append({
                    "category": "bug",
                    "severity": "High",
                    "line": line_number,
                    "title": "Possible division by zero",
                    "description": (
                        f"The divisor '{variable}' was assigned zero earlier. "
                        "Control flow and scopes are not fully tracked."
                    ),
                    "recommendation": (
                        f"Verify that '{variable}' is non-zero before division."
                    ),
                })
                break

        # Update variable state after checking divisions on this line.
        assignment = zero_assignment.match(line)

        if assignment:
            variable, value = assignment.groups()

            if zero_value.fullmatch(value.strip()):
                zero_variables.add(variable)
            else:
                zero_variables.discard(variable)

    return issues
