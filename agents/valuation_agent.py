def estimate_roic(snapshot_metrics):
    """
    Approximate ROIC using available data
    ROIC ≈ NOPAT / Invested Capital
    """

    op_income = snapshot_metrics.get("Operating Income")
    tax_rate = 0.21

    if not op_income:
        return None

    nopat = op_income * (1 - tax_rate)

    # Proxy invested capital (VERY IMPORTANT)
    # Using working capital approximation
    ar = snapshot_metrics.get("Accounts Receivable") or 0
    inv = snapshot_metrics.get("Inventory") or 0
    ap = snapshot_metrics.get("Accounts Payable") or 0

    invested_capital = ar + inv - ap

    # Avoid division issues
    if invested_capital <= 0:
        return None

    roic = nopat / invested_capital

    # sanity bounds
    return max(min(roic, 0.50), -0.10)

def estimate_reinvestment_rate(snapshot_metrics):
    """
    Reinvestment ≈ CapEx / Operating Cash Flow
    Fallback using FCF behavior
    """

    fcf = snapshot_metrics.get("Free Cash Flow")
    op_income = snapshot_metrics.get("Operating Income")

    if not fcf or not op_income:
        return 0.5  # neutral assumption

    # If FCF is low relative to income → high reinvestment
    ratio = fcf / op_income

    reinvestment = 1 - ratio

    # clamp
    return max(min(reinvestment, 0.80), 0.10)



def run_dcf_valuation(data_inputs, event_impact, snapshot_metrics=None, growth_multiplier=1.0, shares_outstanding=None):
    """
    Analyst-grade 2-stage DCF
    """

    # -----------------------------
    # 1️⃣ Inputs
    # -----------------------------
    base_growth = data_inputs.get("Base Growth Rate")

    risk_free = data_inputs.get("Risk Free Rate")
    beta = data_inputs.get("Beta")
    erp = data_inputs.get("Adjusted ERP (Used)")

    event_growth_adj = event_impact.get("Total Growth Adjustment", 0)
    event_discount_adj = event_impact.get("Total Discount Adjustment", 0)

    op_margin = snapshot_metrics.get("Operating Margin")

    # -----------------------------
    # 2️⃣ Discount Rate (CAPM)
    # -----------------------------
    discount = risk_free + beta * erp
    discount += event_discount_adj

    # -----------------------------
    # ROIC-Based Growth
    # -----------------------------
    
    roic = estimate_roic(snapshot_metrics)
    reinvestment = estimate_reinvestment_rate(snapshot_metrics)

    # Build growth components cleanly
    growth_components = []

    # ROIC-driven growth
    if roic is not None and reinvestment is not None:
        growth_components.append(roic * reinvestment)

    # Base growth fallback (only if valid)
    if base_growth is not None:
        growth_components.append(base_growth)

    # If nothing available → skip valuation (no fake numbers)
    if not growth_components:
        raise ValueError("Unable to compute growth: no valid inputs")

    # Combine signals (average = no arbitrary dominance)
    growth = sum(growth_components) / len(growth_components)

    # Add event overlay (safe now)
    if event_growth_adj is not None:
        growth += event_growth_adj

    # Profitability signal
    if op_margin is not None:
        growth += (op_margin - 0.15) * 0.2

    # Apply scenario growth multiplier
    growth *= growth_multiplier
        
    # -----------------------------
    # 4️⃣ Safeguards
    # -----------------------------
    growth = max(min(growth, 0.15), -0.05)
    discount = max(min(discount, 0.20), 0.05)

    if discount <= growth:
        discount = growth + 0.02

    # -----------------------------
    # 5️⃣ Terminal Assumption
    # -----------------------------
    terminal_growth = 0.025

    if discount <= terminal_growth:
        discount = terminal_growth + 0.02

    # -----------------------------
    # 6️⃣ Base Cash Flow
    # -----------------------------
    fcf = snapshot_metrics.get("Free Cash Flow")

    if fcf:
        base_cf = fcf
    elif snapshot_metrics.get("Operating Income"):
        base_cf = snapshot_metrics["Operating Income"] * (1 - 0.21)
    else:
        base_cf = 100

    # -----------------------------
    # 7️⃣ Multi-Stage Projection
    # -----------------------------
    cash_flows = []
    cf = base_cf

    stage1_growth = growth

    # Linear fade (years 4–5)
    stage2_growths = []
    for t in range(4, 6):
        fade = (t - 3) / 2
        g_t = stage1_growth * (1 - fade) + terminal_growth * fade
        stage2_growths.append(g_t)

    growth_schedule = [
        stage1_growth,
        stage1_growth,
        stage1_growth,
        stage2_growths[0],
        stage2_growths[1]
    ]

    for year, g in enumerate(growth_schedule, start=1):
        cf = cf * (1 + g)
        discounted_cf = cf / ((1 + discount) ** year)

        cash_flows.append({
            "year": year,
            "growth": g,
            "projected_cf": cf,
            "discounted_cf": discounted_cf
        })

    # -----------------------------
    # 8️⃣ Terminal Value
    # -----------------------------
    final_cf = cash_flows[-1]["projected_cf"]

    terminal_value = final_cf * (1 + terminal_growth) / (discount - terminal_growth)
    discounted_terminal = terminal_value / ((1 + discount) ** 5)

    # -----------------------------
    # 9️⃣ Intrinsic Value (Enterprise Value)
    # -----------------------------
    pv_cash_flows = sum(cf["discounted_cf"] for cf in cash_flows)
    enterprise_value = pv_cash_flows + discounted_terminal

    terminal_weight = discounted_terminal / enterprise_value if enterprise_value else 0

    # -----------------------------
    # 🔟 Equity Value Conversion
    # -----------------------------
    snapshot_metrics = snapshot_metrics or {}
    cash = snapshot_metrics.get("Cash & Equivalents") or 0
    debt = snapshot_metrics.get("Total Debt") or 0
    net_debt = debt - cash

    equity_value = enterprise_value - net_debt

    intrinsic_per_share = None
    if shares_outstanding and shares_outstanding > 0:
        intrinsic_per_share = equity_value / shares_outstanding

    # -----------------------------
    # 🔟 Diagnostics
    # -----------------------------
    diagnostics = {
        "Base CF": base_cf,
        "Final Year CF": final_cf,
        "Stage 1 Growth": stage1_growth,
        "Terminal Growth": terminal_growth,
        "Discount Rate": discount,
        "Spread (Discount - Growth)": discount - stage1_growth,
        "Terminal Value Contribution (%)": terminal_weight,
        "ROIC": roic,
        "Reinvestment Rate": reinvestment
    }

    if terminal_weight > 0.80:
        print("⚠️ WARNING: Terminal value >80%")

    return {
        "Enterprise Value": enterprise_value,
        "Net Debt": net_debt,
        "Equity Value": equity_value,
        "Intrinsic Value": equity_value, # Maintain for compatibility
        "Intrinsic Value Per Share": intrinsic_per_share,
        "5Y PV Cash Flows": pv_cash_flows,
        "Terminal Value": terminal_value,
        "Terminal Value Contribution (%)": terminal_weight,

        # --- Growth ---
        "Stage 1 Growth": stage1_growth,
        "Stage 2 Growth (Year 4)": growth_schedule[3],
        "Stage 2 Growth (Year 5)": growth_schedule[4],

        # --- Discount ---
        "Discount Used": discount,

        # --- Details ---
        "Projection Details": cash_flows,
        "Diagnostics": diagnostics
    }

def run_scenario_dcf(data_inputs, event_impact, snapshot_metrics=None, shares_outstanding=None):
    """
    Runs the full DCF model separately for Bear, Base, and Bull scenarios.
    """
    import copy

    # Base Case
    base_output = run_dcf_valuation(data_inputs, event_impact, snapshot_metrics, shares_outstanding=shares_outstanding)

    # Bear Case (lower growth, higher discount)
    bear_inputs = copy.deepcopy(data_inputs)
    if bear_inputs and "Adjusted ERP (Used)" in bear_inputs:
        bear_inputs["Adjusted ERP (Used)"] += 0.015
    bear_output = run_dcf_valuation(bear_inputs, event_impact, snapshot_metrics, growth_multiplier=0.8, shares_outstanding=shares_outstanding)

    # Bull Case (higher growth, lower discount)
    bull_inputs = copy.deepcopy(data_inputs)
    if bull_inputs and "Adjusted ERP (Used)" in bull_inputs:
        bull_inputs["Adjusted ERP (Used)"] -= 0.015
    bull_output = run_dcf_valuation(bull_inputs, event_impact, snapshot_metrics, growth_multiplier=1.2, shares_outstanding=shares_outstanding)

    return {
        "Bear": bear_output,
        "Base": base_output,
        "Bull": bull_output
    }