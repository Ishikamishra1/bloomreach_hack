"""
query_globocan_data — the Disease Agent's tool.

CORRECTION from an earlier version of this tool (which incorrectly called
the general WHO GHO OData API). Cancer-specific incidence, mortality and
prevalence by cancer type is NOT in the general WHO GHO API — it's
published by IARC (International Agency for Research on Cancer) as
GLOBOCAN, via the Global Cancer Observatory ("Cancer Today":
https://gco.iarc.who.int/today).

IMPORTANT — GLOBOCAN has no public REST API. It is an interactive
visualization platform with data exports, not a callable service like
ClinicalTrials.gov or openFDA. This means the ingestion pattern for this
one data source is genuinely different from the other three tools:

    query_pubmed, query_clinicaltrials, query_openfda
        -> live API call, every invocation, real-time

    query_globocan_data (this file)
        -> reads a periodically-refreshed export cached in S3, because
           there is nothing to call live

Data ingestion process (manual/semi-automated, NOT a live API call):
    1. Export the relevant cancer-type data from Cancer Today
       (https://gco.iarc.who.int/today) — the platform supports CSV
       export from its data visualization views.
    2. Upload the export to s3://<DATA_BUCKET>/globocan/<cancer_type>.json
       (normalize to JSON at upload time; see scripts/normalize_globocan_export.py
       — not yet built, add before relying on this in a real demo).
    3. This Lambda reads that cached object. It does NOT hit the network.

This is intentionally simple for the MVP: cancer statistics update
annually, not in real time, so a periodically-refreshed cache is the
correct architecture here, not a limitation to work around.
"""
import json
import os
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
BUCKET = os.environ.get("DATA_BUCKET_NAME")


def lambda_handler(event, context):
    """
    Input event shape:
        { "therapeutic_area": "Colorectal Cancer" }
    """
    therapeutic_area = event.get("therapeutic_area", "Colorectal Cancer")
    cache_key = f"globocan/{_slugify(therapeutic_area)}.json"

    if not BUCKET:
        return _error(therapeutic_area, "DATA_BUCKET_NAME not configured")

    try:
        obj = s3.get_object(Bucket=BUCKET, Key=cache_key)
        data = json.loads(obj["Body"].read())
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "NoSuchKey":
            return _error(
                therapeutic_area,
                f"No cached GLOBOCAN export found at s3://{BUCKET}/{cache_key}. "
                f"Export this cancer type from https://gco.iarc.who.int/today "
                f"and upload it before running a scan for this area.",
            )
        return _error(therapeutic_area, f"S3 read failed: {exc}")

    return {
        "agent": "disease_agent",
        "tool": "query_globocan_data",
        "therapeutic_area": therapeutic_area,
        "source": "IARC GLOBOCAN / Global Cancer Observatory (Cancer Today)",
        "data_year": data.get("data_year", "unknown"),
        "record_count": len(data.get("records", [])),
        "records": data.get("records", [])[:50],
    }


def _error(therapeutic_area: str, message: str) -> dict:
    return {
        "agent": "disease_agent",
        "tool": "query_globocan_data",
        "therapeutic_area": therapeutic_area,
        "error": message,
        "records": [],
    }


def _slugify(text: str) -> str:
    return text.strip().lower().replace(" ", "_")
