import re
import os
import json
import google.generativeai as genai

from loader import (
    load_recent_filings,
    extract_8k_filings,
    download_filing_text
)


# ------------------------------------------------
# Detect 8-K Items
# ------------------------------------------------

def detect_item_numbers(text):

    matches = re.findall(r"ITEM\s*([0-9]+\.[0-9]+)", text.upper())

    return list(set(matches))


# ------------------------------------------------
# Detect item section
# ------------------------------------------------

def extract_item_section(text, item):

    pattern = rf"ITEM\s*{item}.*?(?=ITEM\s*[0-9]+\.[0-9]+|$)"

    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

    if match:
        return match.group(0)

    return text


# ------------------------------------------------
# AI Integration Setup
# ------------------------------------------------

def parse_event_with_gemini(text):
    from config import GEMINI_API_KEY
    
    key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if not key:
        print("WARNING: GEMINI_API_KEY not found. Skipping Gemini parsing.")
        return None
        
    genai.configure(api_key=key)

    prompt = f"""
You are an expert financial analyst. Read the following excerpt from an SEC 8-K filing.
Extract any material corporate events and return a strictly formatted JSON object matching this exact schema. If the text does not contain a material financial event (Capital Structure, M&A, Governance, or Legal/Regulatory), return {{"Event Category": "None"}}.

EXPECTED JSON SCHEMA:
{{
  "Event Category": "Capital Structure" | "M&A and Strategic" | "Governance" | "Legal / Regulatory" | "None",
  "Event Type": "<Short Title, e.g. Debt Issuance, Acquisition, Leadership Change>",
  "Event Summary": "<A concise 1-sentence summary of what occurred>",
  "Extracted Structured Data": {{
      // Key-value pairs for numeric/specific data found. MUST BE STRINGS. Example: "Amount": "$500M", "Interest Rate": "2.5%", "Maturity": "2029"
  }},
  "Financial Interpretation": {{
      // Key-value pairs for financial impacts. MUST BE STRINGS. For example: "Leverage": "Increase", "Interest Expense": "Increase", "Integration Risk": "Elevated"
  }}
}}

RAW TEXT TO PARSE:
{text}
"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        content = response.text
        
        # Clean markdown code blocks from response
        if "```json" in content:
            content = content.split("```json")[-1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[-1].split("```")[0]
            
        parsed = json.loads(content.strip())
        
        if parsed.get("Event Category") == "None" or not parsed.get("Event Type"):
            return None
            
        return parsed
    except Exception as e:
        print(f"Gemini parsing failed -> Fallback triggered: {e}")
        return None

# ------------------------------------------------
# Risk Scoring
# ------------------------------------------------

def score_event(event_type, summary_text):
    # Fuzzy match to account for generative variations
    event_str = event_type.lower()
    score = 50
    if "debt" in event_str or "credit" in event_str: score = 70
    elif "equity" in event_str: score = 60
    elif "acquis" in event_str or "merg" in event_str: score = 75
    elif "divest" in event_str or "venture" in event_str: score = 65
    elif "govern" in event_str or "leadership" in event_str: score = 60
    elif "legal" in event_str or "regulat" in event_str: score = 80
    elif "settle" in event_str: score = 65

    text = summary_text.lower()

    # Negative modifiers (increase risk)
    if any(word in text for word in ["investigation", "lawsuit", "default", "decline", "penalty", "violation"]):
        score += 15

    # Positive modifiers (decrease risk)
    if any(word in text for word in ["growth", "expansion", "strategic", "partnership", "acquire"]):
        score -= 15

    return max(0, min(100, score))


# ------------------------------------------------
# Main Event Engine
# ------------------------------------------------

def run_event_engine(cik):

    import math
    from datetime import datetime

    submissions = load_recent_filings(cik)
    filings = extract_8k_filings(submissions)

    reports = []
    seen_events = {}   # dedupe by (year, quarter, event_type)
    today = datetime.now()

    raw_event_count = 0

    # Triggers for Pre-filtering to avoid API spam
    keyword_triggers = [
        "notes", "bond", "revolving", "equity", "share repurchase", "credit agreement", "term loan", 
        "acquire", "acquisition", "merger", "divestiture", "joint venture",
        "chief executive officer", "ceo", "chief financial officer", "cfo", "director", "board",
        "lawsuit", "investigation", "subpoena", "settlement", "litigation", "sec "
    ]

    for filing in filings:

        text = download_filing_text(
            cik,
            filing["accession"],
            filing["accession_nodash"]
        )

        if not text:
            continue
            
        filing_date_str = filing["date"]
        try:
            f_date = datetime.strptime(filing_date_str, "%Y-%m-%d")
        except ValueError:
            continue
            
        years_diff = (today - f_date).days / 365.25
        
        # TIME FILTER (3 Years Max)
        if years_diff > 3.0:
            continue

        quarter = (f_date.month - 1) // 3 + 1
        year = f_date.year
        time_decay = math.exp(-0.5 * years_diff)

        items = detect_item_numbers(text)

        for item in items:
            section = extract_item_section(text, item)

            # Fast text pre-filter to prevent burning Gemini API context window on boilerplate
            if not any(t in section.lower() for t in keyword_triggers):
                continue
                
            parsed_event = parse_event_with_gemini(section)

            if not parsed_event:
                continue

            raw_event_count += 1
            
            event_type = parsed_event["Event Type"]
            summary = parsed_event["Event Summary"]
            cat = parsed_event.get("Event Category", "Unknown")
            
            # Dynamic Scoring
            adj_score = score_event(event_type, summary)
            event_weight = time_decay * (adj_score / 100.0)

            event_dict = {
                "Event Date": filing_date_str,
                "Event Category": cat,
                "Event Type": event_type,
                "Event Summary": summary,
                "Structured Context": parsed_event.get("Extracted Structured Data", {}),
                "Financial Interpretation": parsed_event.get("Financial Interpretation", {}),
                "Time Decay Factor": round(time_decay, 3),
                "Adjusted Risk Score": adj_score,
                "Event Weight": round(event_weight, 3)
            }

            # Lowercase generic event_type key to group identical AI variations (e.g. "Debt Issuance" vs "debt issuance")
            key = (year, quarter, event_type.lower())
            
            # DEDUPLICATION: store the one with highest weight in that quarter
            if key not in seen_events or event_dict["Event Weight"] > seen_events[key]["Event Weight"]:
                seen_events[key] = event_dict

    reports = list(seen_events.values())

    # --- Analytics & Diagnostics ---
    filtered_count = len(reports)
    avg_weight = sum(r["Event Weight"] for r in reports) / filtered_count if filtered_count > 0 else 0

    print("\n--- EVENT ENGINE DIAGNOSTICS ---")
    print(f"Raw Events Detected: {raw_event_count}")
    print(f"Events After 3Yr Filter & Deduplication: {filtered_count}")
    print(f"Average Event Weight: {avg_weight:.3f}")

    if filtered_count > 0:
        reports.sort(key=lambda x: x["Event Weight"], reverse=True)
        print("Top 3 Impactful Events (Gemini Powered):")
        for idx, r in enumerate(reports[:3]):
            print(f"  {idx+1}. [{r['Event Date']}] {r['Event Type']} (W: {r['Event Weight']:.3f}) - {r['Event Summary']}")
    print("--------------------------------\n")

    return reports