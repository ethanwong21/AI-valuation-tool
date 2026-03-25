def generate_investment_signal(valuation_output, market_data, inputs):
    """
    Converts valuation output into interpretable investment signal
    """

    intrinsic_value = valuation_output.get("Intrinsic Value")
    market_price = market_data.get("Market Price")
    shares_outstanding = market_data.get("Shares Outstanding")

    # Convert to per-share value
    intrinsic_per_share = valuation_output.get("Intrinsic Value Per Share")
    if intrinsic_per_share is None and shares_outstanding and shares_outstanding > 0:
        intrinsic_per_share = intrinsic_value / shares_outstanding
    
    growth = valuation_output.get("Stage 1 Growth")
    discount = valuation_output.get("Discount Used")

    raw_erp = inputs.get("Raw ERP (Market Signal)")
    adjusted_erp = inputs.get("Adjusted ERP (Used)")

    # -----------------------------
    # 1️⃣ Valuation Gap
    # -----------------------------
    if not intrinsic_value or not market_price:
        return {"Error": "Missing valuation or market data"}

    upside = (intrinsic_per_share / market_price) - 1

    # -----------------------------
    # 2️⃣ Signal Logic
    # -----------------------------
    if upside > 0.25:
        signal = "Bullish"
        confidence = "Strong Bullish"

    elif upside > 0.10:
        signal = "Bullish"
        confidence = "Moderate Bullish"

    elif upside < -0.25:
        signal = "Bearish"
        confidence = "Strong Bearish"

    elif upside < -0.10:
        signal = "Bearish"
        confidence = "Moderate Bearish"

    else:
        signal = "Neutral"
        confidence = "Low Conviction"

    # -----------------------------
    # 3️⃣ Key Drivers (Interpretability 🔥)
    # -----------------------------
    drivers = []

    # Growth vs Discount dynamic
    spread = discount - growth

    if spread < 0.03:
        drivers.append("Tight discount-growth spread (valuation sensitive)")

    if growth > 0.07:
        drivers.append("Above-average growth assumptions")

    if discount > 0.10:
        drivers.append("Elevated discount rate (risk premium)")

    if raw_erp and adjusted_erp:
        if adjusted_erp > raw_erp:
            drivers.append("ERP floor applied (conservative risk adjustment)")

    if upside > 0.2:
        drivers.append("Significant valuation upside vs market price")

    if upside < -0.2:
        drivers.append("Market pricing implies overvaluation")

    # -----------------------------
    # 4️⃣ Output
    # -----------------------------
    return {
        "Intrinsic Value (Total)": intrinsic_value,
        "Intrinsic Value (Per Share)": intrinsic_per_share,
        "Market Price": market_price,
        "Upside (%)": upside,
        "Signal": signal,
        "Confidence Level": confidence,
        "Key Drivers": drivers,
        "Growth Used": growth,
        "Discount Used": discount,
        "Raw ERP": raw_erp,
        "Adjusted ERP": adjusted_erp
    }


import yfinance as yf

def get_market_data(ticker):
    import yfinance as yf

    stock = yf.Ticker(ticker)
    info = stock.info

    price = info.get("currentPrice")
    shares = info.get("sharesOutstanding")

    if price is None or shares is None:
        raise ValueError("Missing market data")

    return {
        "Market Price": price,
        "Shares Outstanding": shares
    }