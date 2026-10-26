SEVERITY_WEIGHTS = {"Critical": 25, "High": 10, "Medium": 4, "Low": 1}


def calculate_quality_score(issues: list) -> int:
    """100 = perfect, deducts points based on severity."""
    penalty = sum(SEVERITY_WEIGHTS.get(i["severity"], 0) for i in issues)
    score = max(0, 100 - penalty)
    return score


def summarize_severity(issues: list) -> dict:
    summary = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for i in issues:
        if i["severity"] in summary:
            summary[i["severity"]] += 1
    return summary