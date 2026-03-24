# filing_agent.py

# -----------------------------
# Concept Tags
# -----------------------------
CONCEPT_TAGS = {
    "revenue": [
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerExcludingAssessedTax"
    ],
    "cogs": [
        "CostOfGoodsAndServicesSold",
        "CostOfRevenue",
        "CostOfProductsSold"
    ],
    "operating_income": [
        "OperatingIncomeLoss",
        "OperatingIncome"
    ]
}


# -----------------------------
# Generic Extractor
# -----------------------------
def get_concept_value(facts_json, concept_keywords):

    for tag, tag_data in facts_json["facts"]["us-gaap"].items():

        tag_lower = tag.lower()

        if any(keyword in tag_lower for keyword in concept_keywords):

            try:
                units = tag_data.get("units", {})

                if "USD" in units:
                    series = units["USD"]

                    if series:
                        latest = sorted(series, key=lambda x: x["end"])[-1]
                        return latest["val"]

            except:
                continue

    return None


# -----------------------------
# Free Cash Flow (ROBUST)
# -----------------------------
def extract_free_cash_flow(facts_json):

    def get_series_exact(tag_list):
        for tag in tag_list:
            try:
                data = facts_json["facts"]["us-gaap"][tag]["units"]["USD"]
                if data:
                    return sorted(data, key=lambda x: x["end"])
            except:
                continue
        return []

    def get_series_fallback(keywords):
        for tag, tag_data in facts_json["facts"]["us-gaap"].items():
            tag_lower = tag.lower()

            if any(k in tag_lower for k in keywords):
                try:
                    units = tag_data.get("units", {})
                    if "USD" in units:
                        series = units["USD"]
                        if series:
                            return sorted(series, key=lambda x: x["end"])
                except:
                    continue
        return []

    # CFO
    cfo_series = get_series_exact([
        "NetCashProvidedByOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivities"
    ])

    if not cfo_series:
        cfo_series = get_series_fallback([
            "operatingcashflow",
            "cashfromoperations"
        ])

    # CapEx
    capex_series = get_series_exact([
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "CapitalExpenditures"
    ])

    if not capex_series:
        capex_series = get_series_fallback([
            "capitalexpenditure",
            "propertyplant",
            "capex"
        ])

    cfo_values = [x["val"] for x in cfo_series if x.get("val") is not None]
    capex_values = [x["val"] for x in capex_series if x.get("val") is not None]

    if not cfo_values or not capex_values:
        return None

    n = min(len(cfo_values), len(capex_values), 5)

    fcf_values = []
    for i in range(1, n + 1):
        fcf = cfo_values[-i] - abs(capex_values[-i])
        fcf_values.append(fcf)

    return sum(fcf_values) / len(fcf_values)


# -----------------------------
# MAIN ANALYSIS (FIXED)
# -----------------------------
def analyze_filing(facts_json):

    print("Extracting structured financial metrics...")

    # -------- Income Statement --------
    revenue = get_concept_value(
        facts_json,
        ["revenues", "salesrevenue", "revenuefromcontractwithcustomer"]
    )

    if revenue is not None:
        revenue = abs(revenue)  # FIX SIGN

    cogs = get_concept_value(
        facts_json,
        ["costofgoods", "costofrevenue"]
    )

    if cogs is not None:
        cogs = abs(cogs)

    operating_income = get_concept_value(
        facts_json,
        [
            "operatingincomeloss",
            "operatingincome",
            "incomefromoperations"
        ]
    )

    # ----------------------------
    # 🚨 Ignore unreliable Operating Income
    # ----------------------------
    if operating_income is not None and revenue is not None:
        if operating_income < 0 or operating_income < (0.05 * revenue):
            print("⚠️ Ignoring unreliable Operating Income:", operating_income)
            operating_income = None
    
    # -------- Balance Sheet --------
    accounts_receivable = get_concept_value(facts_json, ["receivable"])
    inventory = get_concept_value(facts_json, ["inventory"])
    accounts_payable = get_concept_value(facts_json, ["payable"])

    # -------- Derived Metrics --------
    gross_profit = None
    if revenue is not None and cogs is not None:
        gross_profit = revenue - cogs

    # -------- SAFE MARGINS --------
    gross_margin = None
    if revenue and revenue > 0 and gross_profit is not None:
        gross_margin = gross_profit / revenue

    operating_margin = None
    if revenue and revenue > 0 and operating_income is not None:
        operating_margin = operating_income / revenue

    # sanity filter
    if operating_margin is not None:
        if operating_margin < -1 or operating_margin > 1:
            print("⚠️ Invalid Operating Margin:", operating_margin)
            operating_margin = None

    # -------- Working Capital --------
    dso = None
    if accounts_receivable and revenue and revenue > 0:
        dso = (accounts_receivable / revenue) * 365

    dio = None
    if inventory and cogs and cogs > 0:
        dio = (inventory / cogs) * 365

    dpo = None
    if accounts_payable and cogs and cogs > 0:
        dpo = (accounts_payable / cogs) * 365

    ccc = None
    if dso is not None and dio is not None and dpo is not None:
        ccc = dso + dio - dpo

    # -------- FCF --------
    free_cash_flow = extract_free_cash_flow(facts_json)
    print("DEBUG FCF:", free_cash_flow)

    return {
        "Revenue": revenue,
        "COGS": cogs,
        "Gross Profit": gross_profit,
        "Operating Income": operating_income,
        "Accounts Receivable": accounts_receivable,
        "Inventory": inventory,
        "Accounts Payable": accounts_payable,

        "Gross Margin": gross_margin,
        "Operating Margin": operating_margin,

        "DSO": dso,
        "DIO": dio,
        "DPO": dpo,
        "Cash Conversion Cycle": ccc,

        "Free Cash Flow": free_cash_flow
    }


# -----------------------------
# TIME SERIES HELPERS
# -----------------------------
def get_time_series_usd(facts, tag):
    try:
        return facts["facts"]["us-gaap"][tag]["units"]["USD"]
    except:
        return []


# -----------------------------
# MARGIN SERIES (RESTORED + FIXED)
# -----------------------------
def extract_margin_series(facts_json):

    revenue_series = (
        get_time_series_usd(facts_json, "Revenues")
        or get_time_series_usd(facts_json, "SalesRevenueNet")
        or get_time_series_usd(
            facts_json,
            "RevenueFromContractWithCustomerExcludingAssessedTax"
        )
    )

    possible_tags = [
        "OperatingIncomeLoss",
        "OperatingIncome"
    ]

    op_income_series = []

    for tag in possible_tags:
        series = get_time_series_usd(facts_json, tag)
        if series:
            op_income_series = series
            break

    op_lookup = {o["end"]: o["val"] for o in op_income_series}

    margins = []

    for r in revenue_series:

        revenue = abs(r["val"]) if r["val"] else None
        op_income = op_lookup.get(r["end"])

        if revenue and revenue > 0 and op_income is not None:

            margin = op_income / revenue

            # sanity filter
            if -1 < margin < 1:
                margins.append({
                    "period_end": r["end"],
                    "operating_margin": margin
                })

    margins.sort(key=lambda x: x["period_end"])

    return margins
