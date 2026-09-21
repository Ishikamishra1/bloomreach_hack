"""
enrich_enterprise_data — MOCKED.

This stands in for an authorized enterprise data connection (e.g., a
client's internal research pipeline, portfolio data, or real-world
consumption data — see the Enterprise roadmap discussion in the proposal).

This is intentionally a stub, exactly like the RIS Server in the reference
pipeline diagram. Do not build real enterprise-data integration for the
MVP — it is a Phase 2 item requiring real data-governance conversations
with the client's IT/security team, not a technical afterthought.

In a real deployment this Lambda would instead be replaced with an
AgentCore Gateway target that calls the client's actual authorized API,
under IAM/OAuth scoped access.
"""
import json


def lambda_handler(event, context):
    therapeutic_area = event.get("therapeutic_area", "unknown")

    return {
        "tool": "enrich_enterprise_data",
        "mocked": True,
        "therapeutic_area": therapeutic_area,
        "records": [
            {
                "source": "mocked-enterprise-pipeline",
                "note": (
                    f"No real enterprise data connected. This is a placeholder "
                    f"record for '{therapeutic_area}' — replace with a real "
                    f"AgentCore Gateway target once client data access is "
                    f"authorized."
                ),
            }
        ],
    }
