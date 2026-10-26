import json
from flask import Blueprint, jsonify, request
from utils.auth_middleware import require_auth
from database.mysql import get_connection

history_bp = Blueprint("history", __name__, url_prefix="/api")

@history_bp.route("/history", methods=["GET"])
@require_auth
def get_history():
    user_id = request.current_user["user_id"]

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """SELECT id, file_name, language, quality_score, total_issues, created_at
               FROM analyses
               WHERE user_id = %s
               ORDER BY created_at DESC
               LIMIT 100""",
            (user_id,),
        )
        rows = cursor.fetchall()
        
    finally:
        conn.close()

    for row in rows:
        if row.get("created_at"):
            row["created_at"] = row["created_at"].strftime("%d %b %Y, %I:%M %p")

    return jsonify({"history": rows})


@history_bp.route("/history/<int:analysis_id>", methods=["GET"])
@require_auth
def get_history_detail(analysis_id):
    user_id = request.current_user["user_id"]

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """SELECT id, file_name, language, quality_score, total_issues, full_report, original_code, created_at
                FROM analyses
                WHERE id = %s AND user_id = %s""",
            (analysis_id, user_id),
        )
        row = cursor.fetchone()

    finally:
        conn.close()

    if not row:
        return jsonify({"error": "Report not found."}), 404

    full_report = json.loads(row["full_report"]) if row["full_report"] else {}
    full_report["file_name"] = row["file_name"]
    full_report["original_code"] = row.get("original_code")
    full_report["created_at"] = row["created_at"].strftime("%d %b %Y, %I:%M %p") if row["created_at"] else None

    return jsonify(full_report)


@history_bp.route("/history/<int:analysis_id>", methods=["DELETE"])
@require_auth
def delete_history(analysis_id):
    user_id = request.current_user["user_id"]

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analyses WHERE id = %s AND user_id = %s", (analysis_id, user_id))
        conn.commit()
        deleted = cursor.rowcount
    finally:
        conn.close()

    if deleted == 0:
        return jsonify({"error": "Report not found."}), 404
    return jsonify({"success": True})


@history_bp.route("/history/stats", methods=["GET"])
@require_auth
def get_history_stats():
    user_id = request.current_user["user_id"]

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """SELECT
                   COUNT(*) AS total_files,
                   COALESCE(AVG(quality_score), 0) AS avg_quality,
                   COALESCE(SUM(total_issues), 0) AS total_issues,
                   COALESCE(SUM(critical_count), 0) AS critical_count,
                   COALESCE(SUM(high_count), 0) AS high_count,
                   COALESCE(SUM(medium_count), 0) AS medium_count,
                   COALESCE(SUM(low_count), 0) AS low_count,
                   COALESCE(SUM(bug_count), 0) AS bug_count,
                   COALESCE(SUM(security_count), 0) AS security_count,
                   COALESCE(SUM(performance_count), 0) AS performance_count,
                   COALESCE(SUM(style_count), 0) AS style_count
               FROM analyses
               WHERE user_id = %s""",
            (user_id,),
        )
        stats = cursor.fetchone()
    finally:
        conn.close()

    stats["avg_quality"] = round(float(stats["avg_quality"]), 1)
    total_issues = stats["total_issues"] or 0
    stats["security_risk_pct"] = round((stats["security_count"] / total_issues) * 100, 1) if total_issues > 0 else 0

    return jsonify(stats)

@history_bp.route("/history/latest-stats", methods=["GET"])
@require_auth
def get_latest_stats():
    """Returns stats from the single most recent analysis, plus the
    all-time total file count — used for the Dashboard's snapshot cards."""
    user_id = request.current_user["user_id"]

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """SELECT quality_score, total_issues,
                      critical_count, high_count, medium_count, low_count,
                      bug_count, security_count, performance_count, style_count
               FROM analyses
               WHERE user_id = %s
               ORDER BY created_at DESC
               LIMIT 1""",
            (user_id,),
        )
        latest = cursor.fetchone()

        cursor.execute(
            "SELECT COUNT(*) AS total_files FROM analyses WHERE user_id = %s",
            (user_id,),
        )
        file_count = cursor.fetchone()
    finally:
        conn.close()

    if not latest:
        return jsonify({
            "quality_score": 0, "total_issues": 0,
            "critical_count": 0, "high_count": 0, "medium_count": 0, "low_count": 0,
            "bug_count": 0, "security_count": 0, "performance_count": 0, "style_count": 0,
            "total_files": file_count["total_files"] or 0,
            "security_risk_pct": 0,
        })

    total_issues = latest["total_issues"] or 0
    security_risk_pct = round((latest["security_count"] / total_issues) * 100, 1) if total_issues > 0 else 0

    latest["total_files"] = file_count["total_files"] or 0
    latest["security_risk_pct"] = security_risk_pct
    return jsonify(latest)


@history_bp.route("/history/latest-compare", methods=["GET"])
@require_auth
def get_latest_compare():
    """Finds the most recent analysis (for this user) that has AI-fixed code
    available, so the Dashboard can show a real Code Comparison."""
    user_id = request.current_user["user_id"]

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """SELECT id, file_name, language, full_report, original_code, created_at
               FROM analyses
               WHERE user_id = %s AND full_report IS NOT NULL
               ORDER BY created_at DESC
               LIMIT 20""",
            (user_id,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    for row in rows:
        try:
            report = json.loads(row["full_report"]) if row["full_report"] else {}
        except json.JSONDecodeError:
            continue
        if report.get("fixed_code"):
            report["file_name"] = row["file_name"]
            report["analysis_id"] = row["id"]
            report["original_code"] = row.get("original_code")
            report["created_at"] = row["created_at"].strftime("%d %b %Y, %I:%M %p") if row["created_at"] else None
            return jsonify(report)

    return jsonify({"available": False})