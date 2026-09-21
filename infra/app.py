#!/usr/bin/env python3
"""
TheraScout CDK app.

Deploys three stacks, in dependency order:
  1. DataStack           — S3, OpenSearch Serverless, RDS PostgreSQL
  2. AgentStack           — Lambda tools + IAM roles the agents are allowed to call
  3. OrchestrationStack   — Step Functions state machine + API Gateway + FastAPI (Fargate)

Run:
    cdk bootstrap aws://<ACCOUNT_ID>/us-east-1
    cdk deploy --all
"""
import aws_cdk as cdk

from stacks.data_stack import DataStack
from stacks.agent_stack import AgentStack
from stacks.orchestration_stack import OrchestrationStack

app = cdk.App()

env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1",
)

data_stack = DataStack(app, "TheraScout-Data", env=env)

agent_stack = AgentStack(
    app, "TheraScout-Agents", env=env,
    data_bucket=data_stack.data_bucket,
    metadata_db=data_stack.metadata_db,
)

orchestration_stack = OrchestrationStack(
    app, "TheraScout-Orchestration", env=env,
    tool_functions=agent_stack.tool_functions,
)

app.synth()
