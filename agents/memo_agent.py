# memo_agent.py

def generate_investment_decision(signal_output, scenario_output, risk_report, event_report):
    """
    Synthesizes outputs into a concise, readable investment decision structure defining exact BUY/HOLD/SELL markers.
    Returns:
        decision_dict (dict): Structured sub-dictionaries mapped exactly to Excel injection bounds.
        analyst_paragraph (str): Formal prose explaining the intrinsic valuation context.
        analyst_block (str): Rigidly formatted bullet block defining exact valuation reasons mechanically.
    """

    if not scenario_output or not signal_output:
        return None, None, None

    # --- 1. Top-Level Data Harvesting ---
    base_case = scenario_output.get("Base", {})
    bear_case = scenario_output.get("Bear", {})
    bull_case = scenario_output.get("Bull", {})

    intrinsic_per_share = signal_output.get("Intrinsic Value (Per Share)")
    market_price = signal_output.get("Market Price")
    upside_pct = signal_output.get("Upside (%)", 0)
    signal_raw = signal_output.get("Signal")

    rating_map = {
        "Bullish": "BUY",
        "Neutral": "HOLD",
        "Bearish": "SELL"
    }
    rating = rating_map.get(signal_raw, "HOLD")

    # Scenarios
    bear_val = bear_case.get("Intrinsic Value Per Share", bear_case.get("Intrinsic Value", 0))
    bull_val = bull_case.get("Intrinsic Value Per Share", bull_case.get("Intrinsic Value", 0))

    # Details
    growth = base_case.get("Stage 1 Growth", 0)
    discount = base_case.get("Discount Used", 0)
    diagnostics = base_case.get("Diagnostics", {})
    terminal_contrib = base_case.get("Terminal Value Contribution (%)", 0)
    roic = diagnostics.get("ROIC")

    # --- 2. Analytics ---
    confidence = "Medium"
    if signal_raw == "Bullish" and terminal_contrib < 0.70 and growth > 0.05:
        confidence = "High"
    elif signal_raw == "Bearish" and terminal_contrib > 0.85:
        confidence = "High"
    elif terminal_contrib > 0.90 or abs(upside_pct) < 0.05:
        confidence = "Low"

    drivers = {}
    if growth > 0.05:
        drivers["Driver 1"] = f"Strong baseline revenue growth projected at {growth*100:.1f}%"
    if roic and roic > 0.15:
        drivers["Driver 2"] = f"High returns on invested capital ({roic*100:.1f}%), implying efficient scalable reinvestment."
    if upside_pct > 0.15:
        drivers["Driver 3"] = f"Significant margin of safety projecting {upside_pct*100:.1f}% upside securely to Base intrinsic valuation."
    
    if len(drivers) == 0:
        drivers["Driver 1"] = "Valuation is intrinsically anchored identically to generalized macro baseline assumptions."

    risks = {}
    if terminal_contrib > 0.80:
        risks["Risk 1"] = f"Heavy explicit reliance on Terminal Value constraints ({terminal_contrib*100:.1f}% of overall EV)."
    if discount is not None and growth is not None and (discount - growth < 0.03):
        risks["Risk 2"] = f"Tight spread explicitly between discount rate ({discount*100:.1f}%) and margin growth ({growth*100:.1f}%), hyper-sensitive to macro disruptions."
    
    if isinstance(event_report, list):
        risk_idx = len(risks) + 1
        for e in event_report:
            if e.get("Adjusted Risk Score", 0) >= 60:
                risks[f"Risk {risk_idx}"] = f"Event Risk Threat: {e.get('Event Summary', 'Unknown Entity')}"
                risk_idx += 1
                if risk_idx > 5: break

    if len(risks) == 0:
        risks["Risk 1"] = "Operational risk structures sit precisely isolated inside normalized baseline constraints."

    # Formatter parameters
    def format_pct(val): return f"{val * 100:.1f}%" if val is not None else "N/A"
    def format_usd(val): return f"${val:.2f}" if isinstance(val, (int, float)) else "N/A"

    # --- 3. Generative String Assemblies ---
    analyst_paragraph = (
        f"We formally initiate coverage with an absolute {rating} rating assignment. "
        f"Our rigorously defined base case DCF natively yields an intrinsic value of {format_usd(intrinsic_per_share)}, "
        f"implying an absolute {format_pct(upside_pct)} return against observed execution levels of {format_usd(market_price)}. "
        f"Boundary valuation scenarios rigidly restrict the underlying asset constraints between {format_usd(bear_val)} (Bear downside) and {format_usd(bull_val)} (Assumed Bull execution). "
        f"Downstream forward growth lines securely modeled against {format_pct(growth)} limits, rigorously guarded by a native applied discount rate threshold boundary of {format_pct(discount)}."
    )

    bullet_str = "\n".join([f"- {d}" for d in list(drivers.values())[:4]])
    analyst_block = f"Rating: {rating}\n\nReason:\n{bullet_str}"

    decision_dict = {
        "Summary": {
            "Rating": rating,
            "Intrinsic Value": intrinsic_per_share,
            "Current Price": market_price,
            "Upside (%)": upside_pct,
            "Confidence": confidence
        },
        "Scenarios": {
            "Bear Value": bear_val,
            "Base Value": intrinsic_per_share,
            "Bull Value": bull_val
        },
        "Drivers": drivers,
        "Risks": risks,
        "Diagnostics": {
            "Terminal Value Contribution (%)": terminal_contrib,
            "Spread (Discount - Growth)": discount - growth if discount is not None and growth is not None else None,
            "Overall Operational Risk Score": risk_report.get("Overall Operational Risk Score") if risk_report else None
        }
    }

    return decision_dict, analyst_paragraph, analyst_block
