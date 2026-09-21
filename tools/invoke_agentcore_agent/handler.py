"""
invoke_agentcore_agent — generic bridge between Step Functions and a deployed
AgentCore Runtime agent.

Why this exists: as of this writing, Step Functions does not have a fully
stable, documented *direct* optimized integration for invoking AgentCore
Runtime agents the way it does for classic Bedrock Agents. The reliable,
documented path is Step Functions -> Lambda -> boto3 `bedrock-agentcore`
client. This function is that bridge.

Verify the exact boto3 client name and method signature against the current
AWS SDK before deploying — the AgentCore API surface is new and evolving.
At the time this was written it is the `bedrock-agentcore` client's
`invoke_agent_runtime` action.

Input event shape:
    {
        "agent_runtime_id": "gap_scoring_agent",
        "session_id": "<execution-scoped id, reuse across a single scan>",
        "payload": { ... whatever the agent needs as input ... }
    }
"""
import json
import os
import boto3

_client = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def lambda_handler(event, context):
    agent_runtime_id = event["agent_runtime_id"]
    session_id = event.get("session_id") or context.aws_request_id
    payload = event.get("payload", {})

    response = _client.invoke_agent_runtime(
        agentRuntimeId=agent_runtime_id,
        runtimeSessionId=session_id,
        payload=json.dumps(payload).encode("utf-8"),
    )

    # The response body is typically a streaming or bytes payload depending
    # on how the agent's harness is configured; adjust parsing once the
    # actual agent is deployed and its real response shape is known.
    body = response.get("response")
    if hasattr(body, "read"):
        body = body.read()
    if isinstance(body, bytes):
        body = body.decode("utf-8")

    try:
        parsed = json.loads(body)
    except (TypeError, ValueError):
        parsed = {"raw": body}

    return parsed
