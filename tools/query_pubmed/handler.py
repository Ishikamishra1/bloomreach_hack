"""
query_pubmed — the Research Agent's tool.

Fetches recent scientific literature from PubMed via the NCBI E-utilities
API (free, but rate-limited — request an API key for production volume:
https://www.ncbi.nlm.nih.gov/account/settings/ under "API Key Management").
"""
import json
import urllib.request
import urllib.parse

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def lambda_handler(event, context):
    """
    Input event shape:
        { "therapeutic_area": "Colorectal Cancer", "max_results": 30 }
    """
    therapeutic_area = event.get("therapeutic_area", "Colorectal Cancer")
    max_results = event.get("max_results", 30)

    pmids = _search(therapeutic_area, max_results)
    summaries = _summarize(pmids) if pmids else []

    return {
        "agent": "research_agent",
        "tool": "query_pubmed",
        "therapeutic_area": therapeutic_area,
        "record_count": len(summaries),
        "records": summaries,
    }


def _search(term: str, max_results: int) -> list[str]:
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "term": term,
        "retmax": max_results,
        "retmode": "json",
        "sort": "date",  # most recent first — useful for the Trend Agent too
    })
    url = f"{EUTILS_BASE}/esearch.fcgi?{params}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("esearchresult", {}).get("idlist", [])


def _summarize(pmids: list[str]) -> list[dict]:
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    })
    url = f"{EUTILS_BASE}/esummary.fcgi?{params}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    result = body.get("result", {})
    records = []
    for pmid in result.get("uids", []):
        item = result.get(pmid, {})
        records.append({
            "pmid": pmid,
            "title": item.get("title"),
            "pub_date": item.get("pubdate"),
            "journal": item.get("fulljournalname"),
        })
    return records
