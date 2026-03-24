# working_capital_agent.py

# working_capital_agent.py


# ------------------------------------------------
# Concept → Possible XBRL Tags
# ------------------------------------------------

CONCEPT_TAGS = {

    "revenue": [
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerExcludingAssessedTax"
    ],

    "cogs": [
        "CostOfGoodsAndServicesSold",
        "CostOfRevenue",
        "CostOfProductsSold",
        "CostsAndExpenses"
    ],

    "accounts_receivable": [
        "AccountsReceivableNetCurrent",
        "ReceivablesNetCurrent"
    ],

    "inventory": [
        "InventoryNet",
        "InventoryFinishedGoods"
    ],

    "accounts_payable": [
        "AccountsPayableCurrent",
        "AccountsPayableTradeCurrent"
    ]
}


# ------------------------------------------------
# Universal Series Loader
# ------------------------------------------------

def get_concept_series(facts_json, concept):

    for tag in CONCEPT_TAGS[concept]:

        try:
            series = facts_json["facts"]["us-gaap"][tag]["units"]["USD"]

            if series:
                #print(f"Using {concept} tag:", tag)
                return series

        except:
            continue

    #print(f"No tag found for concept: {concept}")
    return []


# ------------------------------------------------
# Build Working Capital Series
# ------------------------------------------------

def build_wc_series(facts_json):

    revenue_series = get_concept_series(facts_json, "revenue")
    cogs_series = get_concept_series(facts_json, "cogs")
    ar_series = get_concept_series(facts_json, "accounts_receivable")
    inv_series = get_concept_series(facts_json, "inventory")
    ap_series = get_concept_series(facts_json, "accounts_payable")

    wc_series = []

    for r in revenue_series:

        period = r["end"]
        revenue = r["val"]

        cogs = next((x["val"] for x in cogs_series if x["end"] == period), None)
        ar = next((x["val"] for x in ar_series if x["end"] == period), None)
        inv = next((x["val"] for x in inv_series if x["end"] == period), None)
        ap = next((x["val"] for x in ap_series if x["end"] == period), None)

        if revenue and cogs and ar and ap:

            dso = (ar / revenue) * 365
            dio = (inv / cogs) * 365 if inv else 0
            dpo = (ap / cogs) * 365

            ccc = dso + dio - dpo

            wc_series.append({
                "period_end": period,
                "DSO": dso,
                "DIO": dio,
                "DPO": dpo,
                "CCC": ccc
            })

    wc_series.sort(key=lambda x: x["period_end"])

    return wc_series


# ------------------------------------------------
# Calculate Changes
# ------------------------------------------------

def calculate_wc_deltas(wc_series):

    if len(wc_series) < 4:
        return None

    latest = wc_series[-1]
    prev_q = wc_series[-2]
    prev_y = wc_series[-4]

    return {

        "DSO_YoY": latest["DSO"] - prev_y["DSO"],
        "DIO_YoY": latest["DIO"] - prev_y["DIO"],
        "DPO_YoY": latest["DPO"] - prev_y["DPO"],
        "CCC_YoY": latest["CCC"] - prev_y["CCC"],

        "DSO_QoQ": latest["DSO"] - prev_q["DSO"],
        "DIO_QoQ": latest["DIO"] - prev_q["DIO"],
        "DPO_QoQ": latest["DPO"] - prev_q["DPO"],
        "CCC_QoQ": latest["CCC"] - prev_q["CCC"]
    }


# ------------------------------------------------
# Pattern Classification
# ------------------------------------------------

def classify_wc_pattern(deltas):

    if not deltas:
        return "Insufficient data"

    if deltas["DIO_YoY"] > 10 and deltas["CCC_YoY"] > 10:
        return "Demand Slowdown"

    if deltas["DPO_YoY"] > 10:
        return "Liquidity Pressure"

    if deltas["DSO_YoY"] > 10:
        return "Credit Deterioration"

    if deltas["CCC_YoY"] < -10:
        return "Efficiency Improvement"

    return "Stable Working Capital"


# ------------------------------------------------
# Main Working Capital Engine
# ------------------------------------------------

def run_working_capital_engine(facts_json, snapshot_metrics):

    wc_series = build_wc_series(facts_json)

    deltas = calculate_wc_deltas(wc_series)

    if not deltas:

        return {
            "Pattern Classification": "Insufficient data",
            "Working Capital Direction": None,
            "Cash Efficiency Signal": None,
            "Operational Stress Flag": None
        }

    pattern = classify_wc_pattern(deltas)

    direction = "Improving" if deltas["CCC_YoY"] < 0 else "Deteriorating"

    cash_signal = (
        "Cash Tailwind"
        if deltas["CCC_YoY"] < 0
        else "Cash Headwind"
    )

    stress_flag = pattern in [
        "Demand Slowdown",
        "Liquidity Pressure",
        "Credit Deterioration"
    ]

    return {

        "Pattern Classification": pattern,
        "Working Capital Direction": direction,
        "Cash Efficiency Signal": cash_signal,
        "Operational Stress Flag": stress_flag,

        **deltas
    }