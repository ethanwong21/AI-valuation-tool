# margin_diagnostic_agent.py

def calculate_deltas(margin_series):

    if len(margin_series) < 5:
        return None

    latest = margin_series[-1]
    prev_q = margin_series[-2]
    prev_y = margin_series[-5]  # approx YoY if quarterly

    delta_qoq = latest["operating_margin"] - prev_q["operating_margin"]
    delta_yoy = latest["operating_margin"] - prev_y["operating_margin"]

    return delta_qoq, delta_yoy


def classify_margin_driver(mda_text):

    text = mda_text.lower()

    if "cost" in text or "inflation" in text:
        return "Cost-driven pressure"

    if "volume decline" in text or "lower demand" in text:
        return "Volume decline"

    if "pricing" in text or "price increases" in text:
        return "Pricing power"

    if "mix" in text:
        return "Mix shift"

    if "leverage" in text or "scale" in text:
        return "Operating leverage"

    return "Unclassified"


def structural_assessment(delta_yoy, driver):

    if delta_yoy < 0 and driver in ["Cost-driven pressure", "Volume decline"]:
        return "Structural Risk", 0.75

    if delta_yoy > 0 and driver in ["Pricing power", "Operating leverage"]:
        return "Structural Strength", 0.25

    return "Temporary Movement", 0.5


def run_margin_diagnostic(margin_series, mda_text):

    deltas = calculate_deltas(margin_series)

    if not deltas:
        return "Insufficient data"

    delta_qoq, delta_yoy = deltas

    trend = "Expansion" if delta_yoy > 0 else "Compression"

    driver = classify_margin_driver(mda_text)

    assessment, risk_score = structural_assessment(delta_yoy, driver)

    return {
        "QoQ Delta": delta_qoq,
        "YoY Delta": delta_yoy,
        "Trend Direction": trend,
        "Primary Driver": driver,
        "Structural Assessment": assessment,
        "Risk Persistence Score": risk_score
    }