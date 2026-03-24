import re

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
# Event Detection (Keyword Based)
# ------------------------------------------------

def detect_event_type(text):

    text = text.lower()

    # Capital structure events
    if any(word in text for word in [
        "senior notes",
        "notes due",
        "bond issuance",
        "aggregate principal amount",
        "term loan",
        "credit agreement",
        "revolving credit facility",
        "convertible notes"
    ]):
        return "Debt Issuance"

    # Acquisition events
    if any(word in text for word in [
        "acquire",
        "acquisition",
        "merger agreement",
        "purchase agreement"
    ]):
        return "Acquisition"

    # Legal / regulatory events
    if any(word in text.lower() for word in [
        "sec investigation",
        "department of justice investigation",
        "doj investigation",
        "filed lawsuit",
        "litigation against",
        "subpoena"
    ]):
        return "Legal Proceeding"
    return None


# ------------------------------------------------
# Governance Detection
# ------------------------------------------------

def detect_governance(item, text):

    if item != "5.02":
        return None

    text = text.lower()

    if "chief executive officer" in text or "ceo" in text:
        return "CEO leadership change"

    if "chief financial officer" in text or "cfo" in text:
        return "CFO leadership change"

    if "chief operating officer" in text or "coo" in text:
        return "COO leadership change"

    return "Executive leadership change"


# ------------------------------------------------
# Debt Extraction
# ------------------------------------------------

def extract_debt_summary(text):

    pattern = re.search(
        r"aggregate principal amount of\s+\$[0-9,]+\s+of\s+[0-9.]+%\s+notes?\s+due\s+[0-9]{4}",
        text,
        re.IGNORECASE
    )

    if pattern:
        phrase = pattern.group()

        amount = re.search(r"\$[0-9,]+", phrase)
        rate = re.search(r"[0-9.]+%", phrase)
        maturity = re.search(r"due\s+[0-9]{4}", phrase, re.I)

        parts = []

        if amount:
            parts.append(amount.group())

        if rate:
            parts.append(rate.group())

        if maturity:
            parts.append(maturity.group())

        return "Debt issuance " + " ".join(parts) + " Notes"

    return "Debt issuance announced"

# ------------------------------------------------
# Acquisition Summary
# ------------------------------------------------

def extract_acquisition_summary(text):

    target = re.search(
        r"acquire(?:d)?\s+([A-Z][A-Za-z0-9&\s]{2,40})",
        text
    )

    value = re.search(
        r"\$[0-9,.]+\s*(million|billion)?",
        text,
        re.I
    )

    if target and value:
        return f"Acquired {target.group(1)} for {value.group()}"

    if target:
        return f"Acquired {target.group(1)}"

    return "Acquisition announced"


# ------------------------------------------------
# Legal Summary
# ------------------------------------------------

def extract_legal_summary(text):

    text = text.lower()

    if "sec investigation" in text:
        return "SEC investigation disclosed"

    if "department of justice investigation" in text:
        return "DOJ investigation disclosed"

    if "litigation" in text or "lawsuit" in text:
        return "Litigation disclosed"

    if "subpoena" in text:
        return "Regulatory subpoena disclosed"

    return None

# ------------------------------------------------
# Risk Scoring
# ------------------------------------------------

def score_event(event):

    scores = {

        "Debt Issuance": 70,
        "Acquisition": 75,
        "Governance Change": 60,
        "Legal Proceeding": 80
    }

    return scores.get(event, 50)


# ------------------------------------------------
# Main Event Engine
# ------------------------------------------------

def run_event_engine(cik):

    submissions = load_recent_filings(cik)

    filings = extract_8k_filings(submissions)

    reports = []

    seen_events = set()   # prevents duplicates


    for filing in filings:

        text = download_filing_text(
            cik,
            filing["accession"],
            filing["accession_nodash"]
        )

        if not text:
            continue

        items = detect_item_numbers(text)

        for item in items:

            section = extract_item_section(text, item)


            # -----------------------------
            # Governance Events
            # -----------------------------

            gov = detect_governance(item, section)

            if gov:

                event_type = "Governance Change"

                key = (filing["date"], event_type)

                if key in seen_events:
                    continue

                seen_events.add(key)

                reports.append({

                    "Event Date": filing["date"],
                    "Event Type": event_type,
                    "Event Summary": gov,
                    "Event Risk Score": score_event(event_type)

                })

                continue


            # -----------------------------
            # Detect Event Type
            # -----------------------------

            event_type = detect_event_type(section)

            if not event_type:
                continue


            key = (filing["date"], event_type)

            if key in seen_events:
                continue

            seen_events.add(key)


            # -----------------------------
            # Build Event Summary
            # -----------------------------

            if event_type == "Debt Issuance":

                summary = extract_debt_summary(section)

            elif event_type == "Acquisition":

                summary = extract_acquisition_summary(section)

            elif event_type == "Legal Proceeding":

                summary = extract_legal_summary(section)

                if summary is None:
                    continue

            else:
                continue


            # -----------------------------
            # Save Event
            # -----------------------------

            reports.append({

                "Event Date": filing["date"],
                "Event Type": event_type,
                "Event Summary": summary,
                "Event Risk Score": score_event(event_type)

            })


    return reports