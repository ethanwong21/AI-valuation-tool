# Code/main.py

import os
import sys
import pandas as pd


from config import FRED_API_KEY

from loader import load_company_facts, get_cik_from_ticker
from agents.filing_agent import analyze_filing, extract_margin_series
from agents.margin_diagnostic_agent import run_margin_diagnostic
from agents.working_capital_agent import run_working_capital_engine
from agents.risk_scoring_agent import run_risk_scoring_layer
from agents.event_engine_agent import run_event_engine
from agents.event_impact_agent import aggregate_event_impacts
from agents.valuation_agent import run_dcf_valuation
from agents.signal_agent import generate_investment_signal, get_market_data

try:
    from agents.data_inputs_agent import build_data_inputs
    HAS_DATA_INPUTS = True
except:
    HAS_DATA_INPUTS = False

def human_format(num):
    if num is None:
        return None

    try:
        num = float(num)
    except:
        return num

    if abs(num) >= 1e12:
        return f"{num/1e12:.2f}T"
    elif abs(num) >= 1e9:
        return f"{num/1e9:.2f}B"
    elif abs(num) >= 1e6:
        return f"{num/1e6:.2f}M"
    elif abs(num) >= 1e3:
        return f"{num/1e3:.2f}K"
    else:
        return round(num, 4)

def to_vertical_df(data_dict):

    # Strict: only handle dicts properly
    if isinstance(data_dict, dict):
        return pd.DataFrame(
            list(data_dict.items()),
            columns=["Metric", "Value"]
        )

    # If something went wrong, show FULL debug
    return pd.DataFrame(
        [{"Metric": "DEBUG", "Value": repr(data_dict)}]
    )

def run_analysis(ticker):

    os.makedirs("Code/outputs", exist_ok=True)

    print(f"\n===== RUNNING WORKFLOW FOR {ticker.upper()} =====")

    # ----------------------------------
    # 1️⃣ Pull EDGAR Structured Data
    # ----------------------------------
    facts_json = load_company_facts(ticker)

    # ----------------------------------
    # 2️⃣ Snapshot Financial Metrics
    # ----------------------------------
    snapshot_metrics = analyze_filing(facts_json)
    print("Snapshot metrics computed.")

    # ----------------------------------
    # 3️⃣ Margin Diagnostic
    # ----------------------------------
    margin_series = extract_margin_series(facts_json)
    margin_report = run_margin_diagnostic(margin_series, "")

    # ----------------------------------
    # 🔗 Inject REAL Operating Metrics (FINAL)
    # ----------------------------------
    if margin_series and len(margin_series) > 0:

        latest_margin = margin_series[-1]["operating_margin"]

        snapshot_metrics["Operating Margin"] = latest_margin

        revenue = snapshot_metrics.get("Revenue")

        if revenue and latest_margin:
            reconstructed_income = revenue * latest_margin
            snapshot_metrics["Operating Income"] = reconstructed_income

        print("Injected Operating Margin:", latest_margin)
        print("Reconstructed Operating Income:", reconstructed_income)

    else:
        print("⚠️ No margin series available")
        
    # ----------------------------------
    # 4️⃣ Working Capital
    # ----------------------------------
    wc_report = run_working_capital_engine(
        facts_json,
        snapshot_metrics
    )
    print("Working capital diagnostic computed.")

    # ----------------------------------
    # 5️⃣ Event Intelligence
    # ----------------------------------
    cik = get_cik_from_ticker(ticker)
    event_report = run_event_engine(cik)
    print("Event intelligence computed.")

    # ----------------------------------
    # 6️⃣ Event Impact (Component 3)
    # ----------------------------------
    event_impact = aggregate_event_impacts(event_report)
    print("Event impact computed.")

    # ----------------------------------
    # 7️⃣ Risk Scoring
    # ----------------------------------
    risk_report = run_risk_scoring_layer(
        margin_report,
        wc_report,
        snapshot_metrics
    )
    print("Risk scoring computed.")

    # ----------------------------------
    # 8️⃣ Data Inputs (Component 1)
    # ----------------------------------
    data_inputs = None

    if HAS_DATA_INPUTS:
        try:
            data_inputs = build_data_inputs(
                ticker,
                snapshot_metrics,
                margin_report,
                risk_report,
                FRED_API_KEY
            )

            print("Data inputs computed.")

        except Exception as e:
            print("❌ DATA INPUTS FAILED:", e)
            raise e
        

    # ----------------------------------
    # 9️⃣ Excel Output
    # ----------------------------------
    output_path = f"Code/outputs/{ticker.upper()}_analysis.xlsx"

    # ----------------------------------
    # 🔟 Valuation Engine (NEW)
    # ----------------------------------
    valuation_output = None

    if data_inputs:
        valuation_output = run_dcf_valuation(
            data_inputs,
            event_impact,
            snapshot_metrics
        )

        print("Valuation computed.")

    # ----------------------------------
    # 1️⃣1️⃣ Signal Generation (NEW)
    # ----------------------------------
    signal_output = None

    if valuation_output and data_inputs:

        market_data = get_market_data(ticker)

        signal_output = generate_investment_signal(
            valuation_output,
            market_data,
            data_inputs
        )

        print("Signal generated.")

    # ----------------------------------
    # 🔗 Combine Valuation + Signal
    # ----------------------------------
    combined_output = None

    if valuation_output and signal_output:

        combined_output = {}

        # --- Signal ---
        combined_output["Signal"] = signal_output.get("Signal")
        combined_output["Confidence Level"] = signal_output.get("Confidence Level")
        combined_output["Upside (%)"] = signal_output.get("Upside (%)")
        combined_output["Market Price"] = signal_output.get("Market Price")
        combined_output["Shares Outstanding"] = market_data.get("Shares Outstanding")
        combined_output["Intrinsic Value (Total)"] = valuation_output.get("Intrinsic Value")
        combined_output["Intrinsic Value (Per Share)"] = signal_output.get("Intrinsic Value (Per Share)")

        # --- Valuation ---
        combined_output["5Y PV Cash Flows"] = valuation_output.get("5Y PV Cash Flows")
        combined_output["Terminal Value"] = valuation_output.get("Terminal Value")
        combined_output["Terminal Value Contribution (%)"] = valuation_output.get("Terminal Value Contribution (%)")

        # --- Assumptions ---
        combined_output["Growth Used"] = valuation_output.get("Growth Used")
        combined_output["Discount Used"] = valuation_output.get("Discount Used")
        combined_output["Raw ERP"] = signal_output.get("Raw ERP")
        combined_output["Adjusted ERP"] = signal_output.get("Adjusted ERP")

        # --- Drivers ---
        drivers = signal_output.get("Key Drivers", [])
        for i, d in enumerate(drivers):
            combined_output[f"Driver {i+1}"] = d

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:

        # ----------------------------------
        # 01️⃣ Financial Analysis (COMBINED)
        # ----------------------------------
        sheet_name = "01_Financial_Analysis"
        row = 0

        # Snapshot
        snapshot_df = to_vertical_df(snapshot_metrics)
        snapshot_df.to_excel(writer, sheet_name=sheet_name, startrow=row, index=False)

        row += len(snapshot_df) + 2

        # Margins Header
        pd.DataFrame([["--- MARGINS ---"]]).to_excel(
            writer, sheet_name=sheet_name, startrow=row, index=False, header=False
        )

        row += 1

        # Margins
        margin_df = to_vertical_df(margin_report)
        margin_df.to_excel(writer, sheet_name=sheet_name, startrow=row, index=False)

        row += len(margin_df) + 2

        # Working Capital Header
        pd.DataFrame([["--- WORKING CAPITAL ---"]]).to_excel(
            writer, sheet_name=sheet_name, startrow=row, index=False, header=False
        )

        row += 1

        # Working Capital
        wc_df = to_vertical_df(wc_report)
        wc_df.to_excel(writer, sheet_name=sheet_name, startrow=row, index=False)

        # ----------------------------------
        # 02️⃣ Event Intelligence
        # ----------------------------------
        pd.DataFrame(event_report).to_excel(
            writer, sheet_name="02_Events", index=False
        )

        # ----------------------------------
        # 03️⃣ Risk
        # ----------------------------------
        to_vertical_df(risk_report).to_excel(
            writer, sheet_name="03_Risk", index=False
        )

        # ----------------------------------
        # 04️⃣ Data Inputs
        # ----------------------------------
        if data_inputs:
            to_vertical_df(data_inputs).to_excel(
                writer, sheet_name="04_Data_Inputs", index=False
            )

        # ----------------------------------
        # 05️⃣ Event Impact
        # ----------------------------------
        to_vertical_df(event_impact).to_excel(
            writer, sheet_name="05_Event_Impact", index=False
        )

        from openpyxl.styles import Font, PatternFill

        # ----------------------------------
        # 06️⃣ Valuation + Signal (COMBINED)
        # ----------------------------------
        if combined_output:
            to_vertical_df(combined_output).to_excel(
                writer, sheet_name="06_Valuation_Signal", index=False
            )

            ws = writer.sheets["06_Valuation_Signal"]

            # -----------------------------
            # Styles
            # -----------------------------
            bold_font = Font(bold=True)

            green_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
            red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
            yellow_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")

            # -----------------------------
            # Bold header
            # -----------------------------
            for cell in ws[1]:
                cell.font = bold_font

            # -----------------------------
            # Loop through rows
            # -----------------------------
            for row in ws.iter_rows(min_row=2):
                metric_cell = row[0]
                value_cell = row[1]

                metric = str(metric_cell.value)

                # -----------------------------
                # FORMAT NUMBERS
                # -----------------------------
                if isinstance(value_cell.value, (int, float)):

                    # Percent fields
                    if any(x in metric for x in ["%", "Growth", "Discount", "Contribution"]):
                        value_cell.number_format = '0.00%'

                    # Large numbers
                    elif abs(value_cell.value) >= 1_000_000:
                        value_cell.number_format = '#,##0'

                    else:
                        value_cell.number_format = '0.00'

                # -----------------------------
                # COLOR LOGIC (🔥 KEY PART)
                # -----------------------------

                # Signal coloring
                if metric == "Signal":
                    if value_cell.value == "Bullish":
                        value_cell.fill = green_fill
                    elif value_cell.value == "Bearish":
                        value_cell.fill = red_fill
                    else:
                        value_cell.fill = yellow_fill

                # Upside coloring
                if metric == "Upside (%)" and isinstance(value_cell.value, (int, float)):
                    if value_cell.value > 0.10:
                        value_cell.fill = green_fill
                    elif value_cell.value < -0.10:
                        value_cell.fill = red_fill
                    else:
                        value_cell.fill = yellow_fill

                # Highlight confidence
                if metric == "Confidence Level":
                    value_cell.font = Font(bold=True)

                # Highlight intrinsic value (important metric)
                if metric == "Intrinsic Value":
                    value_cell.font = Font(bold=True)

    print(f"\nExcel report saved: {output_path}")
    print("\n===== ANALYSIS COMPLETE =====")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python Code/main.py TICKER")
        sys.exit()

    ticker_input = sys.argv[1]
    run_analysis(ticker_input)