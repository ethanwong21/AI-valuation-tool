def run_dcf_valuation(data_inputs, event_impact, snapshot_metrics=None):
    """
    Multi-year DCF valuation engine with event-adjusted assumptions
    """

    # -----------------------------
    # 1️⃣ Extract Inputs
    # -----------------------------
    base_growth = data_inputs.get("Base Growth Rate")
    base_discount = data_inputs.get("Base Discount Rate")

    event_growth_adj = event_impact.get("Total Growth Adjustment", 0)
    event_discount_adj = event_impact.get("Total Discount Adjustment", 0)

    # -----------------------------
    # 2️⃣ Apply Adjustments
    # -----------------------------
    
    growth = base_growth + event_growth_adj
    discount = base_discount + event_discount_adj

    # -----------------------------
    # Forward-looking adjustments
    # -----------------------------

    # Profitability signal
    op_margin = snapshot_metrics.get("Operating Margin")

    #temp debug
    print("DEBUG op_margin:", op_margin)

    if op_margin is not None:

        # -----------------------------
        # Growth adjustments (quality-driven)
        # -----------------------------
        if op_margin > 0.25:
            growth += 0.02
            growth = max(growth, 0.06)   # 🔥 STRONG floor
        elif op_margin > 0.15:
            growth += 0.01
            growth = max(growth, 0.05)
        elif op_margin < 0.10:
            growth -= 0.01

    # -----------------------------
    # Risk adjustment
    # -----------------------------
    if discount > 0.10:
        growth -= 0.005  # reduce penalty (was too harsh)

    # -----------------------------
    # Strength adjustment (discount)
    # -----------------------------
    if op_margin and op_margin > 0.25:
        discount -= 0.015   # 🔥 slightly stronger reduction
    
    # -----------------------------
    # Discount cap for quality firms
    # -----------------------------
    if op_margin and op_margin > 0.20:
        discount = min(discount, 0.085)

    # -----------------------------
    # 3️⃣ Safeguards (CRITICAL)
    # -----------------------------
    # Cap extreme values
    growth = max(min(growth, 0.15), -0.05)        # -5% to 15%
    discount = max(min(discount, 0.20), 0.05)     # 5% to 20%

    # -----------------------------
    # Spread control (CRITICAL)
    # -----------------------------
    if discount - growth > 0.05:
        growth += 0.01  # tighten unrealistic gap

    # Ensure discount > growth
    if discount <= growth:
        discount = growth + 0.02  # enforce spread


    # -----------------------------
    # 4️⃣ Starting Cash Flow (UPDATED)
    # -----------------------------

    fcf = snapshot_metrics.get("Free Cash Flow")

    
    if fcf is not None:
        base_cf = fcf
    elif snapshot_metrics.get("Operating Income"):
        # fallback ONLY if FCF missing
        tax_rate = 0.21
        base_cf = snapshot_metrics["Operating Income"] * (1 - tax_rate)
    else:
        base_cf = 100  # last resort fallback
    
    # -----------------------------
    # 5️⃣ 5-Year Projection
    # -----------------------------
    cash_flows = []
    cf = base_cf

    for year in range(1, 6):
        cf = cf * (1 + growth)
        discounted_cf = cf / ((1 + discount) ** year)

        cash_flows.append({
            "year": year,
            "projected_cf": cf,
            "discounted_cf": discounted_cf
        })

    # -----------------------------
    # 6️⃣ Terminal Value
    # -----------------------------
    terminal_growth = 0.025  # justified: long-term GDP/inflation anchor

    final_cf = cash_flows[-1]["projected_cf"]

    # Safety buffer to prevent explosion
    spread = discount - terminal_growth

    if spread < 0.015:
        spread = 0.015  # enforce minimum spread

    terminal_value = final_cf * (1 + terminal_growth) / spread

    discounted_terminal = terminal_value / ((1 + discount) ** 5)

    # -----------------------------
    # 7️⃣ Intrinsic Value
    # -----------------------------
    pv_cash_flows = sum(cf["discounted_cf"] for cf in cash_flows)

    intrinsic_value = pv_cash_flows + discounted_terminal

    terminal_weight = discounted_terminal / intrinsic_value if intrinsic_value else 0

    # -----------------------------
    # 🚨 Terminal Warning (ADD HERE)
    # -----------------------------
    if terminal_weight > 0.80:
        print("⚠️ WARNING: Terminal value dominates valuation (>80%)")
    elif terminal_weight > 0.70:
        print("⚠️ Notice: High terminal dependence (>70%)")
    
    # -----------------------------
    # 9️⃣ Diagnostics (NEW)
    # -----------------------------
    diagnostics = {
        "Base CF": base_cf,
        "Final Year CF": final_cf,
        "Sum PV (5Y)": pv_cash_flows,
        "Discount - Growth Spread": discount - growth,
        "Terminal Spread": discount - terminal_growth
    }

    # -----------------------------
    # 8️⃣ Output
    # -----------------------------
    return {
        "Intrinsic Value": intrinsic_value,
        "Growth Used": growth,
        "Discount Used": discount,
        "Terminal Value": terminal_value,
        "Terminal Value Contribution (%)": terminal_weight,
        "5Y PV Cash Flows": pv_cash_flows,
        **diagnostics
    }