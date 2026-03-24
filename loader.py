import requests
import re

from config import SEC_USER_EMAIL


if not SEC_USER_EMAIL:
    raise ValueError("SEC_USER_EMAIL not set in config")

SEC_HEADERS = {
    "User-Agent": f"Ethan Wong {SEC_USER_EMAIL}"
}


def get_cik_from_ticker(ticker):
    url = "https://www.sec.gov/files/company_tickers.json"
    response = requests.get(url, headers=SEC_HEADERS)
    data = response.json()

    for company in data.values():
        if company["ticker"].lower() == ticker.lower():
            return str(company["cik_str"]).zfill(10)

    raise ValueError("CIK not found")


def load_company_facts(ticker):
    print(f"Fetching EDGAR data for {ticker}...")

    cik = get_cik_from_ticker(ticker)

    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    response = requests.get(url, headers=SEC_HEADERS)

    if response.status_code != 200:
        raise Exception("Failed to fetch EDGAR data")

    return response.json()


def load_recent_filings(cik):
    """
    Pull recent filings metadata from SEC
    Includes 8-K, 10-Q, 10-K etc
    """

    url = f"https://data.sec.gov/submissions/CIK{cik}.json"

    response = requests.get(url, headers=SEC_HEADERS)

    if response.status_code != 200:
        raise Exception("Failed to fetch submissions")

    return response.json()


def extract_8k_filings(submissions_json):

    filings = submissions_json["filings"]["recent"]

    events = []

    for form, acc, date in zip(
        filings["form"],
        filings["accessionNumber"],
        filings["filingDate"]
    ):

        if form == "8-K":

            events.append({
                "accession": acc,
                "accession_nodash": acc.replace("-", ""),
                "date": date
            })

    return events[:50]


def download_filing_text(cik, accession, accession_nodash):

    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_nodash}/{accession}.txt"

    r = requests.get(url, headers=SEC_HEADERS)

    if r.status_code != 200:
        return ""

    return r.text