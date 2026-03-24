# risk_scoring_agent.py

def score_margin_health(margin_report):

    if not isinstance(margin_report, dict):
        return 50

    delta_yoy = margin_report.get("YoY Delta", 0)
    assessment = margin_report.get("Structural Assessment", "")

    score = 50

    # Directional component
    if delta_yoy > 0:
        score += 20
    else:
        score -= 20

    # Structural component
    if assessment == "Structural Strength":
        score += 20
    elif assessment == "Structural Risk":
        score -= 20

    return max(0, min(100, score))


def score_working_capital(wc_report):

    if not isinstance(wc_report, dict):
        return 50

    ccc_yoy = wc_report.get("CCC_YoY", 0)
    pattern = wc_report.get("Pattern Classification", "")

    score = 50

    # Improving cash cycle
    if ccc_yoy < 0:
        score += 20
    else:
        score -= 20

    # Penalize stress patterns
    if pattern in [
        "Demand Slowdown",
        "Liquidity Pressure",
        "Credit Deterioration"
    ]:
        score -= 20

    if pattern == "Efficiency Improvement":
        score += 10

    return max(0, min(100, score))


def score_liquidity(snapshot_metrics):

    cash = snapshot_metrics.get("CashAndCashEquivalentsAtCarryingValue")
    current_assets = snapshot_metrics.get("Revenue")  # placeholder logic
    current_liabilities = snapshot_metrics.get("Accounts Payable")

    if not current_liabilities:
        return 50

    # Very simple proxy (can expand later)
    ratio = (cash or 0) / current_liabilities

    if ratio > 1:
        return 80
    if ratio > 0.5:
        return 60
    return 30


def compute_overall_risk(margin_score, wc_score, liquidity_score):

    # Higher score = healthier company
    composite = (
        0.4 * margin_score +
        0.3 * wc_score +
        0.3 * liquidity_score
    )

    if composite > 75:
        rating = "Low Operational Risk"
    elif composite > 55:
        rating = "Moderate Operational Risk"
    else:
        rating = "Elevated Operational Risk"

    return composite, rating


def run_risk_scoring_layer(margin_report, wc_report, snapshot_metrics):

    margin_score = score_margin_health(margin_report)
    wc_score = score_working_capital(wc_report)
    liquidity_score = score_liquidity(snapshot_metrics)

    composite, rating = compute_overall_risk(
        margin_score,
        wc_score,
        liquidity_score
    )

    return {
        "Margin Health Score": margin_score,
        "Working Capital Efficiency Score": wc_score,
        "Liquidity Stress Indicator": liquidity_score,
        "Overall Operational Risk Score": composite,
        "Overall Operational Risk Rating": rating
    }


