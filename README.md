# 📊 AI-Augmented Valuation Engine

A Python-based financial analysis system that integrates **SEC filings, macro data, and event-driven signals** to produce **dynamic, forward-looking equity valuations and investment signals**.

---

## Overview

This project builds an end-to-end valuation pipeline that moves beyond static DCF models by incorporating:

* Financial data from SEC EDGAR filings
* Macro inputs (risk-free rate, equity risk premium)
* Event-driven adjustments (legal, governance, capital structure)
* Forward-looking valuation logic
* Automated investment signal generation

---

## System Architecture

```text
SEC Filings (EDGAR)
        ↓
Financial Extraction (Revenue, FCF, Margins)
        ↓
Event Intelligence Engine
        ↓
Risk + Macro Inputs (FRED, Beta, ERP)
        ↓
Valuation Engine (DCF)
        ↓
Signal Generation Layer
        ↓
Structured Output (Excel)
```

---

## Key Features

### 📊 Financial Analysis

* Extracts revenue, margins, working capital, and free cash flow from XBRL data
* Normalizes inconsistent filings and reconstructs key metrics
* Computes operational diagnostics (CCC, DSO, DIO, DPO)

---

### Event Intelligence

* Detects corporate events from filings:

  * Governance changes
  * Capital structure adjustments
  * Legal risks
* Translates events into:

  * Growth adjustments
  * Discount rate adjustments

---

### Valuation Engine

* Multi-year Discounted Cash Flow (DCF) model
* Uses event-adjusted growth and discount rates
* Anchored by Free Cash Flow and terminal value logic
* Includes safeguards on growth/discount spreads and terminal dependence

---

### Signal Generation

* Converts valuation outputs into interpretable signals:

  * **Bullish / Bearish / Neutral**
* Adds confidence levels and key drivers for transparency

---

### Reporting Layer

* Produces structured outputs combining:

  * Financial metrics
  * Event analysis
  * Risk diagnostics
  * Valuation results
  * Investment signal

---

## Methodology

The system is designed to reflect how analysts think by:

* Linking **corporate events** to valuation assumptions
* Dynamically adjusting growth and discount rates
* Moving away from static inputs toward **forward-looking modeling**

---

## Tech Stack

* Python
* Pandas
* OpenPyXL
* Requests
* SEC EDGAR API
* FRED API

---

## Future Improvements

* Scenario analysis (Bull / Base / Bear)
* Sensitivity analysis (growth vs discount)

---

## Motivation

Traditional valuation models are often static and fail to reflect real-world developments.

This project aims to build a system that is:

* Dynamic
* Data-driven
* Economically grounded

---

## Disclaimer

This project is for educational and research purposes only and does not constitute investment advice.

---

## Author

Ethan Wong
Finance, Accounting & Economics student 
Purdue University 
| Interested in Markets and Tech
