"""
check_data_scope — backs the "Public data sufficient?" decision diamond.

MVP implementation: deliberately simple, rule-based, no LLM call. This is
intentional — Milestone build order treats this as plain logic, not an
agent, since "do we recognize this therapeutic area" doesn't need
reasoning, just a lookup. Upgrade to an LLM-backed check later only if the
rule-based version proves too rigid (e.g., handling synonyms/typos in the
cancer type name).
"""
import json
import os

# MVP-scoped: specific cancer types with a cached GLOBOCAN export
# (see tools/query_globocan_data) and reasonable public-data coverage
# across all four sources. "Oncology" alone is too broad to scope an MVP
# demo around — each cancer type has very different data volume. Extend
# as more cancer types are onboarded (upload their GLOBOCAN export first).
KNOWN_THERAPEUTIC_AREAS = {"colorectal cancer"}


def lambda_handler(event, context):
    therapeutic_area = event.get("therapeutic_area", "").strip().lower()

    sufficient = therapeutic_area in KNOWN_THERAPEUTIC_AREAS

    return {
        "therapeutic_area": therapeutic_area,
        "sufficient": sufficient,
        "reason": (
            "Recognized therapeutic area with public data source mappings."
            if sufficient else
            "Therapeutic area not yet mapped to public data sources — "
            "routing to enterprise data enrichment."
        ),
    }
