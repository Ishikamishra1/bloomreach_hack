"""
query_openfda — the Treatment Agent's tool.

Fetches approved medicine / drug label data from the openFDA API (free,
no key required for low-volume use; register for a key to raise rate
limits before any real demo).

Docs: https://open.fda.gov/apis/drug/label/
"""
import json
import urllib.request
import urllib.parse
import urllib.error

OPENFDA_BASE = "https://api.fda.gov/drug/label.json"


def lambda_handler(event, context):
    """
    Input event shape:
        { "therapeutic_area": "Colorectal Cancer", "max_results": 30 }
    """
    therapeutic_area = event.get("therapeutic_area", "Colorectal Cancer")
    max_results = event.get("max_results", 30)

    try:
        records = _search(therapeutic_area, max_results)
    except urllib.error.URLError as exc:
        return {
            "agent": "treatment_agent",
            "tool": "query_openfda",
            "therapeutic_area": therapeutic_area,
            "error": str(exc),
            "records": [],
        }

    return {
        "agent": "treatment_agent",
        "tool": "query_openfda",
        "therapeutic_area": therapeutic_area,
        "record_count": len(records),
        "records": records,
    }


def _search(term: str, max_results: int) -> list[dict]:
    params = urllib.parse.urlencode({
        "search": f'indications_and_usage:"{term}"',
        "limit": max_results,
    })
    url = f"{OPENFDA_BASE}?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    records = []
    for result in body.get("results", []):
        openfda = result.get("openfda", {})
        records.append({
            "brand_name": (openfda.get("brand_name") or [None])[0],
            "generic_name": (openfda.get("generic_name") or [None])[0],
            "manufacturer": (openfda.get("manufacturer_name") or [None])[0],
            "indications": (result.get("indications_and_usage") or [""])[0][:500],
            "warnings": (result.get("warnings") or [""])[0][:500],
        })
    return records
