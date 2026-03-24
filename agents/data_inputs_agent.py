# agents/data_inputs_agent.py

import requests
import yfinance as yf


# ------------------------------------------------
# 1. Risk-Free Rate (FRED: 10Y Treasury)
# ------------------------------------------------

def get_risk_free_rate(api_key):

    if not api_key:
        raise ValueError("FRED API key missing")

    url = (
        "https://api.stlouisfed.org/fred/series/observations"
        "?series_id=DGS10"
        f"&api_key={api_key}"
        "&file_type=json"
    )

    response = requests.get(url)
    data = response.json()

    observations = data.get("observations", [])

    for obs in reversed(observations):
        if obs["value"] != ".":
            return float(obs["value"]) / 100

    raise ValueError("No valid risk-free rate found")


# ------------------------------------------------
# 2. Equity Risk Premium (Damodaran proxy)
# ------------------------------------------------

def get_equity_risk_premium(risk_free_rate):
    """
    Market-implied ERP using SPY earnings yield
    """

    import yfinance as yf

    spy = yf.Ticker("SPY")

    info = spy.info

    pe_ratio = info.get("trailingPE")

    # Robust validation
    if pe_ratio is None or pe_ratio <= 0:
        raise Exception("Invalid P/E ratio from SPY")

    earnings_yield = 1 / pe_ratio

    raw_erp = earnings_yield - risk_free_rate

    adjusted_erp = max(raw_erp, 0.03)  # used for valuation

    return {
        "Raw ERP (Market Signal)": raw_erp,
        "Adjusted ERP (Used)": adjusted_erp,
    }

# ------------------------------------------------
# 3. Beta (Market Data via Yahoo Finance)
# ------------------------------------------------

def get_beta(ticker):

    stock = yf.Ticker(ticker)
    info = stock.info

    beta = info.get("beta")

    if beta is None:
        raise ValueError("Beta not available")

    return float(beta)


# ------------------------------------------------
# 4. Growth Estimation (Your System)
# ------------------------------------------------

def estimate_base_growth(snapshot_metrics, margin_report):

    operating_margin = snapshot_metrics.get("Operating Margin")
    trend = margin_report.get("Trend Direction")

    if trend == "Expansion":
        return 0.06

    if trend == "Compression":
        return 0.03

    if operating_margin and operating_margin > 0.15:
        return 0.07

    return 0.04


# ------------------------------------------------
# 5. Discount Rate (CAPM + Internal Risk Layer)
# ------------------------------------------------

def estimate_discount_rate(risk_free, beta, adjusted_erp, risk_report):

    base = risk_free + beta * adjusted_erp

    risk_score = risk_report.get("Overall Operational Risk Score", 50)

    adjustment = (50 - risk_score) / 1000

    return base + adjustment


# ------------------------------------------------
# 6. MAIN ENTRY
# ------------------------------------------------

def build_data_inputs(
    ticker,
    snapshot_metrics,
    margin_report,
    risk_report,
    fred_api_key
):

    risk_free = get_risk_free_rate(fred_api_key)

    erp_data = get_equity_risk_premium(risk_free)
    raw_erp = erp_data["Raw ERP (Market Signal)"]
    adjusted_erp = erp_data["Adjusted ERP (Used)"]
    
    beta = get_beta(ticker)

    growth = estimate_base_growth(snapshot_metrics, margin_report)

    discount = estimate_discount_rate(
        risk_free,
        beta,
        adjusted_erp,
        risk_report
    )

    return {
        "Base Growth Rate": growth,
        "Base Discount Rate": discount,
        "Risk Free Rate": risk_free,
        "Raw ERP (Market Signal)": raw_erp,
        "Adjusted ERP (Used)": adjusted_erp,
        "Beta": beta
    }