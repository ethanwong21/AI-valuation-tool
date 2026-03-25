# memo_agent.py

def generate_investment_memo(signal_output, scenario_output, risk_report, event_report):
    """
    Synthesizes outputs into a concise, readable investment memo structure.
    Returns:
        memo_dict (dict): A structured dictionary organized by section for easy exporting.
        memo_text (str): A natural language summary of the valuation.
    """

    # Ensure there's enough data to build the memo
    if not scenario_output or not signal_output:
        return None, None

    # --- 1. Top-Level Data Harvesting ---
    base_case = scenario_output.get("Base", {})
    bear_case = scenario_output.get("Bear", {})
    bull_case = scenario_output.get("Bull", {})

    intrinsic_per_share = signal_output.get("Intrinsic Value (Per Share)")
    market_price = signal_output.get("Market Price")
    upside_pct = signal_output.get("Upside (%)")
    signal_eval = signal_output.get("Signal")

    # Scenarios
    bear_val = bear_case.get("Intrinsic Value Per Share", bear_case.get("Intrinsic Value"))
    bull_val = bull_case.get("Intrinsic Value Per Share", bull_case.get("Intrinsic Value"))

    # Drivers
    growth = base_case.get("Stage 1 Growth")
    discount = base_case.get("Discount Used")
    
    diagnostics = base_case.get("Diagnostics", {})
    roic = diagnostics.get("ROIC")
    reinvestment = diagnostics.get("Reinvestment Rate")

    # Risk
    risk_score = risk_report.get("Overall Operational Risk Score") if risk_report else None
    
    # Extract latest highest-priority risk summary from events if it exists
    key_event_risks = []
    if isinstance(event_report, list):
        for e in event_report:
            if e.get("Event Risk Score", 0) >= 60:
                key_event_risks.append(e.get("Event Summary", "Unknown Risk Event"))
    
    key_event_str = ", ".join(key_event_risks) if key_event_risks else "No high-risk events detected."

    # Diagnostics
    terminal_contrib = base_case.get("Terminal Value Contribution (%)")
    spread = discount - growth if discount is not None and growth is not None else None

    # --- 2. String Formatting Helper ---
    def format_pct(val):
        return f"{val * 100:.1f}%" if val is not None else "N/A"

    def format_usd(val):
        return f"${val:.2f}" if isinstance(val, (int, float)) else "N/A"

    # --- 3. Build Natural Language Memo ---
    memo_text = (
        f"The model estimates an intrinsic value of {format_usd(intrinsic_per_share)}, "
        f"implying {format_pct(upside_pct)} upside from the current price of {format_usd(market_price)}.\n"
        f"Under a bear case, value falls to {format_usd(bear_val)}, "
        f"while the bull case reaches {format_usd(bull_val)}.\n"
        f"Growth is driven by an estimated ROIC of {format_pct(roic)} "
        f"and reinvestment rate of {format_pct(reinvestment)}."
    )

    # --- 4. Build Structured Sections Dictionary ---
    memo_dict = {
        "Summary": {
            "Investment Signal": signal_eval,
            "Intrinsic Value (Base Case)": intrinsic_per_share,
            "Current Price": market_price,
            "Upside (%)": upside_pct
        },
        "Scenarios": {
            "Bear Value": bear_val,
            "Base Value": intrinsic_per_share,
            "Bull Value": bull_val
        },
        "Drivers": {
            "Growth Assumption (Stage 1)": growth,
            "Discount Rate": discount,
            "ROIC": roic,
            "Reinvestment Rate": reinvestment
        },
        "Risk Summary": {
            "Key Risks": key_event_str,
            "Risk Score": risk_score
        },
        "Valuation Diagnostics": {
            "Terminal Value Contribution (%)": terminal_contrib,
            "Spread (Discount - Growth)": spread
        }
    }

    return memo_dict, memo_text
