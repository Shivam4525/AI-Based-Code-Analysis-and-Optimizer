import json
import re
from flask import Blueprint, request, jsonify
from analyzers.registry import get_analyzer, supported_languages
from services.language_detector import detect_language
from services.scoring import calculate_quality_score, summarize_severity
from services.ollama import generate_explanation_and_fix, OllamaError
from services.validation import validate_fixed_code
from services import js_tools
from services.snippet_extractor import extract_snippet
from utils.auth_middleware import get_user_from_token
from database.mysql import execute
from services.ollama import get_explanation
from services.js_fixer import fix_javascript, get_risky_suggestions
from analyzers.security import scan_security
from collections import Counter

analyze_bp = Blueprint("analyze", __name__, url_prefix="/api")

def _is_safe_list_subprocess_finding(finding, code):
    """
    Allow contextual Bandit B603/B607 warnings only when the
    finding points to a subprocess call using an argument list
    without shell=True. The warnings remain visible in reports.
    """
    import ast

    rule_id = finding.get("rule_id")
    if rule_id not in {"B603", "B607"}:
        return False

    try:
        tree = ast.parse(code)
    except (SyntaxError, TypeError):
        return False

    finding_line = finding.get("line")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if getattr(node, "lineno", None) != finding_line:
            continue

        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr in {"run", "Popen", "call", "check_call", "check_output"}
            and isinstance(func.value, ast.Name)
            and func.value.id == "subprocess"
        ):
            continue

        shell_true = any(
            keyword.arg == "shell"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in node.keywords
        )
        if shell_true:
            continue

        if node.args and isinstance(node.args[0], (ast.List, ast.Tuple)):
            return True

    return False

@analyze_bp.route("/languages", methods=["GET"])
def list_languages():
    return jsonify({"supported": supported_languages()})


@analyze_bp.route("/analyze", methods=["POST"])
def analyze_code():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    filename = data.get("filename") or "pasted_code"
    requested_lang = data.get("language", "auto")
    use_ai = data.get("use_ai", True)

    if not code.strip():
        return jsonify({"error": "No code provided"}), 400

    code_lines = code.count("\n") + 1
    if code_lines > 600 and use_ai:
        use_ai = False
        force_ai_skip_reason = f"Code has {code_lines} lines â€” AI fix generation was skipped automatically for very large files. Static analysis results are still complete below."
    else:
        force_ai_skip_reason = None

    lang = requested_lang if requested_lang != "auto" else detect_language(filename, code)

    # If this is JavaScript detected from an HTML file, extract just the <script> contents
    if lang == "javascript" and re.search(r'<!DOCTYPE\s+html|<html[\s>]', code, re.I):
        scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', code, re.S | re.I)
        extracted = "\n\n".join(s.strip() for s in scripts if s.strip())
        if extracted:
            code = extracted

    analyzer = get_analyzer(lang)
    if not analyzer:
        return jsonify({
            "error": f"Language '{lang}' is not supported yet.",
            "detected_language": lang,
            "supported": supported_languages(),
        }), 400

    # Run the existing language analyzer first.
    issues = analyzer.safe_analyze(code, filename)

    # Run deterministic security rules independently of the AI model.
    security_findings = scan_security(code, lang)

    # Avoid adding the exact same finding twice.
    existing = {
        (
            item.get("category"),
            item.get("line"),
            item.get("title"),
        )
        for item in issues
    }

    for finding in security_findings:
        key = (
            finding.get("category"),
            finding.get("line"),
            finding.get("title"),
        )

        if key not in existing:
            issues.append(finding)
            existing.add(key)

    # Attach a code snippet to each issue so the frontend can show "original code"
    for issue in issues:
        issue["original_snippet"] = extract_snippet(code, issue.get("line", 0))

    score = calculate_quality_score(issues)
    fixed_quality_score = None
    severity_summary = summarize_severity(issues)

    category_counts = {"bug": 0, "security": 0, "performance": 0, "style": 0}
    for issue in issues:
        cat = issue.get("category")
        if cat in category_counts:
            category_counts[cat] += 1

    ai_explanation = None
    fixed_code = None
    ai_error = None
    risky_suggestions = []

    if use_ai:
        try:
            
            if lang == "javascript":
                final_code, notes, fixed_count = fix_javascript(code, issues)
                risky_suggestions = get_risky_suggestions(code, final_code, issues)

                if not isinstance(final_code, str) or not final_code.strip():
                    ai_error = "JavaScript fix rejected: generated code is empty."
                elif final_code.strip() == code.strip() and not risky_suggestions:
                    ai_error = (
                        "No verified-safe automatic fix was found for this code. "
                        + (" ".join(notes) if notes else "No rejection details were recorded.")
                    )
                else:
                    syntax_valid, syntax_error = js_tools.node_check(final_code)

                    if not syntax_valid:
                        ai_error = (
                            "JavaScript fix rejected: syntax validation failed. "
                            f"{syntax_error or 'Unknown syntax error.'}"
                        )
                    elif final_code.strip() != code.strip():
                        fixed_code = final_code

                        try:
                            ai_explanation = get_explanation(lang, issues)
                        except OllamaError:
                            ai_explanation = (
                                "JavaScript automatic fixes passed syntax validation. "
                                "AI summary unavailable."
                            )

                        if notes:
                            ai_explanation += " " + " ".join(notes)
            else:
                ai_result = generate_explanation_and_fix(lang, code, issues)
                validation = validate_fixed_code(
                    lang,
                    ai_result["fixed_code"],
                    original_code=code,
                )

                if validation["valid"] is True:
                    ai_explanation = ai_result["explanation"]
                    fixed_code = validation["code"]

                elif validation["valid"] is False:
                    ai_error = (
                        "AI fix was rejected by validation: "
                        f"{validation.get('error') or 'Validation failed.'}"
                    )

                else:
                    ai_error = (
                        "AI-generated code was not accepted because it "
                        "could not be verified. "
                        f"{validation.get('error') or 'Validation unavailable.'}"
                    )

        except OllamaError as e:
            ai_error = str(e) 


    # Re-scan the candidate with the language analyzer and custom security rules.
    verification_status = "not_run"
    fixed_issues = []
    resolved_issues = []
    remaining_issues = []
    new_issues = []
    unresolved_security = []
    newly_detected_security = []
    rejected_candidate_issues = []

    if fixed_code is not None:
        before_security = [
            issue for issue in issues
            if issue.get("category") == "security"
        ]

        after_analyzed = analyzer.safe_analyze(fixed_code, filename)

        # Preserve all analyzer findings for reporting if verification rejects
        # the candidate. Do not expose the rejected code as fixed_code.
        rejected_candidate_issues = list(after_analyzed)

        after_security = [
            issue for issue in after_analyzed
            if issue.get("category") == "security"
        ]

        scanned_security = scan_security(fixed_code, lang)
        after_security.extend(scanned_security)

        # Preserve custom security findings as well.
        rejected_candidate_issues.extend(scanned_security)

        # Remove exact duplicate findings from the combined scanners.
        deduplicated = []
        seen_findings = set()
        for finding in after_security:
            key = (
                finding.get("rule_id", ""),
                finding.get("category", ""),
                finding.get("line", 0),
                finding.get("title", ""),
            )
            if key not in seen_findings:
                seen_findings.add(key)
                deduplicated.append(finding)
        after_security = deduplicated

        def security_signature(finding):
            rule_id = finding.get("rule_id")
            if rule_id:
                return ("rule", rule_id)
            category = (finding.get("category") or "").casefold().strip()
            title = " ".join(
                (finding.get("title") or "").casefold().split()
            )
            return ("title", category, title)

        before_counts = Counter(
            security_signature(finding) for finding in before_security
        )
        after_counts = Counter(
            security_signature(finding) for finding in after_security
        )

        # Existing findings are unresolved only when the same finding
        # still exists in the candidate, up to the original count.
        unresolved_security = []
        newly_detected_security = []
        
        matched_counts = Counter()

        for finding in after_security:
            signature = security_signature(finding)

            if matched_counts[signature] < before_counts[signature]:
                matched_counts[signature] += 1

                # Keep the existing generic subprocess-import warning visible.
                if finding.get("rule_id") == "B404":
                    continue

                unresolved_security.append(finding)

            else:
                # Allow only verified list-based subprocess warnings.
                # These findings remain visible in the report, but do not
                # independently reject the candidate.
                if (
                    finding.get("rule_id") in {"B603", "B607"}
                    and _is_safe_list_subprocess_finding(finding, fixed_code)
                ):
                    continue

                newly_detected_security.append(finding)



        if unresolved_security:
            ai_error = (
                "AI-generated code still has security findings after re-scan. "
                "The candidate was not accepted as security-verified. "
                "Review the remaining findings."
            )
            fixed_code = None
            verification_status = "rejected_security_check"
            ai_explanation = (
                "The AI-generated fix was rejected because security findings "
                "remain after re-scan. No fixed code was accepted. "
                "Review security_rejection_details for the unresolved findings."
            )

        elif newly_detected_security:
            ai_error = (
                "AI-generated code introduced additional security findings. "
                "The candidate was not accepted as security-verified."
            )
            fixed_code = None
            verification_status = "rejected_security_check"
            ai_explanation = (
                "The AI-generated fix was rejected because the re-scan detected "
                "additional security findings. No fixed code was accepted. "
                "Review security_rejection_details for the new findings."
            )

        else:
            verification_status = "security_rescan_passed"
    # Re-analyze the accepted fixed code using the same analyzers.
    resolved_issues = []
    remaining_issues = []
    new_issues = []

    if fixed_code is not None and verification_status == "security_rescan_passed":
        fixed_issues = analyzer.safe_analyze(fixed_code, filename)

        # Add the same independent security scan used for original code.
        fixed_security = scan_security(fixed_code, lang)

        fixed_existing = {
            (
                item.get("category"),
                item.get("line"),
                item.get("title"),
            )
            for item in fixed_issues
        }

        for finding in fixed_security:
            key = (
                finding.get("category"),
                finding.get("line"),
                finding.get("title"),
            )
            if key not in fixed_existing:
                fixed_issues.append(finding)
                fixed_existing.add(key)

        # Attach snippets from the corrected code.
        for issue in fixed_issues:
            issue["original_snippet"] = extract_snippet(
                fixed_code, issue.get("line", 0)
            )



        # Match findings using category, normalized title, and rule ID.
        # This helps distinguish findings reported by different scanners.

        def issue_signature(issue):
            rule_id = (issue.get("rule_id") or "").strip().upper()
            category = (issue.get("category") or "").casefold().strip()
            title = " ".join(
                (issue.get("title") or "").casefold().split()
            )

            # Prefer scanner rule IDs when both findings have them.
            if rule_id:
                return ("rule", category, rule_id)

            return ("title", category, title)


        # Match original findings against the fixed-code findings.
        fixed_available = Counter(
            issue_signature(issue) for issue in fixed_issues
        )

        resolved_issues = []

        for issue in issues:
            signature = issue_signature(issue)

            if fixed_available[signature] > 0:
                fixed_available[signature] -= 1
            else:
                resolved_issues.append(issue)

        # Classify findings from the fixed-code scan.
        original_available = Counter(
            issue_signature(issue) for issue in issues
        )

        remaining_issues = []
        new_issues = []


        for issue in fixed_issues:
            signature = issue_signature(issue)

            if original_available[signature] > 0:
                original_available[signature] -= 1
                remaining_issues.append(issue)
            else:
                new_issues.append(issue)

        fixed_quality_score = calculate_quality_score(fixed_issues)


 
    # Make the summary reflect the verified fixed-code results.
    if (
        fixed_code is not None
        and verification_status == "security_rescan_passed"
    ):
        resolved_count = len(resolved_issues)
        remaining_count = len(remaining_issues)
        new_count = len(new_issues)

        summary_parts = [
            "The AI-generated code passed the configured security re-scan checks; this does not guarantee complete security."
        ]

        if resolved_count:
            summary_parts.append(
                f"{resolved_count} original issue(s) were resolved."
            )

        if remaining_count:
            summary_parts.append(
                f"{remaining_count} original issue(s) remain in the fixed code."
            )

        if new_count:
            summary_parts.append(
                f"{new_count} additional finding(s) were detected in the fixed code; review them before using the code."
            )

        ai_explanation = " ".join(summary_parts)
               

    response_payload = {
        "language": lang,
        "quality_score": score,
        "original_quality_score": score,
        "fixed_quality_score": fixed_quality_score,
        "total_issues": len(issues),
        "severity_summary": severity_summary,
        "issues": issues,
        "fixed_issues": fixed_issues if verification_status == "security_rescan_passed" else [],
        "rejected_candidate_issues": (
            rejected_candidate_issues
            if verification_status == "rejected_security_check"
            else []
        ),
        "ai_explanation": ai_explanation,
        "fixed_code": fixed_code,
        "verification_status": verification_status,
        "ai_error": ai_error or force_ai_skip_reason,
        "risky_suggestions": risky_suggestions if lang == "javascript" and use_ai else [],
        "resolved_issues": resolved_issues,
        "remaining_issues": remaining_issues,
        "new_issues": new_issues,
    }

    user = get_user_from_token()
    analysis_id = None
    if user:
        try:
            analysis_id = execute(
                """INSERT INTO analyses
                    (user_id, file_name, language, quality_score, total_issues, full_report,
                    critical_count, high_count, medium_count, low_count,
                    bug_count, security_count, performance_count, style_count, original_code)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    user["user_id"], filename, lang, score, len(issues), json.dumps(response_payload),
                    severity_summary.get("Critical", 0), severity_summary.get("High", 0),
                    severity_summary.get("Medium", 0), severity_summary.get("Low", 0),
                    category_counts["bug"], category_counts["security"],
                    category_counts["performance"], category_counts["style"], code,
                ),
            )
            
        except Exception as e:
            print(f"Warning: could not save analysis history: {e}")

    response_payload["security_rejection_details"] = {
        "unresolved": [
            {
                "rule_id": item.get("rule_id"),
                "severity": item.get("severity"),
                "title": item.get("title"),
                "line": item.get("line"),
            }
            for item in unresolved_security
        ],
        "newly_detected": [
            {
                "rule_id": item.get("rule_id"),
                "severity": item.get("severity"),
                "title": item.get("title"),
                "line": item.get("line"),
            }
            for item in newly_detected_security
        ],
    }

    response_payload["analysis_id"] = analysis_id
    return jsonify(response_payload)

