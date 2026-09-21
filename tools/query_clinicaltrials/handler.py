"""
query_clinicaltrials — the Clinical Trial Agent's tool.

Fetches trial records from the ClinicalTrials.gov API v2 (free, no key
required). Also used as the MVP stand-in data source for the Competition
Agent (sponsor field indicates which organizations are active in a space).

Docs: https://clinicaltrials.gov/data-api/api
"""
import json
import urllib.request
import urllib.parse
import urllib.error

CTGOV_BASE = "https://clinicaltrials.gov/api/v2/studies"


def lambda_handler(event, context):
    """
    Input event shape:
        { "therapeutic_area": "Colorectal Cancer", "max_results": 30 }
    """
    therapeutic_area = event.get("therapeutic_area", "Colorectal Cancer")
    max_results = event.get("max_results", 30)

    try:
        studies = _search(therapeutic_area, max_results)
    except urllib.error.URLError as exc:
        return {
            "agent": "clinical_trial_agent",
            "tool": "query_clinicaltrials",
            "therapeutic_area": therapeutic_area,
            "error": str(exc),
            "records": [],
        }

    return {
        "agent": "clinical_trial_agent",
        "tool": "query_clinicaltrials",
        "therapeutic_area": therapeutic_area,
        "record_count": len(studies),
        "records": studies,
    }


def _search(term: str, max_results: int) -> list[dict]:
    params = urllib.parse.urlencode({
        "query.cond": term,
        "pageSize": max_results,
        "fields": "NCTId,BriefTitle,OverallStatus,Phase,LeadSponsorName,Condition",
    })
    url = f"{CTGOV_BASE}?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    records = []
    for study in body.get("studies", []):
        protocol = study.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        design = protocol.get("designModule", {})
        sponsor = protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
        records.append({
            "nct_id": ident.get("nctId"),
            "title": ident.get("briefTitle"),
            "status": status.get("overallStatus"),
            "phase": design.get("phases"),
            "sponsor": sponsor.get("name"),
        })
    return records
