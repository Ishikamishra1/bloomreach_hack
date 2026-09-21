"""
OrchestrationStack — turns orchestration/statemachine.asl.json into a real
Step Functions state machine, and fronts it with an API Gateway endpoint
that the FastAPI backend (or frontend directly) can call.

This is the literal implementation of the pipeline diagram:
    ingest -> Choice(public data sufficient?) -> Parallel(6 agents) ->
    gap_score -> report -> Stop
"""
import json
import os

from aws_cdk import (
    Stack, Duration,
    aws_stepfunctions as sfn,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_iam as iam,
)
from constructs import Construct


class OrchestrationStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str,
        tool_functions: dict[str, _lambda.Function],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Load the state machine definition and substitute real Lambda ARNs
        # for the placeholder tokens (e.g. "${QueryGlobocanDataArn}") left in the
        # checked-in ASL file, so the same JSON file is both documentation
        # and the deployable definition.
        asl_path = os.path.join(os.path.dirname(__file__), "..", "..", "orchestration", "statemachine.asl.json")
        with open(asl_path) as f:
            definition_str = f.read()

        substitutions = {
            "QueryGlobocanDataArn": tool_functions["query_globocan_data"].function_arn,
            "QueryPubmedArn": tool_functions["query_pubmed"].function_arn,
            "QueryClinicalTrialsArn": tool_functions["query_clinicaltrials"].function_arn,
            "QueryOpenFdaArn": tool_functions["query_openfda"].function_arn,
            "CheckDataScopeArn": tool_functions["check_data_scope"].function_arn,
            "EnrichEnterpriseDataArn": tool_functions["enrich_enterprise_data"].function_arn,
            "InvokeAgentCoreAgentArn": tool_functions["invoke_agentcore_agent"].function_arn,
            "ComposePdfReportArn": tool_functions["compose_pdf_report"].function_arn,
        }
        for key, value in substitutions.items():
            definition_str = definition_str.replace(f"${{{key}}}", value)

        self.state_machine = sfn.StateMachine(
            self, "TheraScoutPipeline",
            state_machine_name="TheraScoutOpportunityScan",
            definition_body=sfn.DefinitionBody.from_string(definition_str),
            timeout=Duration.minutes(10),
        )

        for fn in tool_functions.values():
            fn.grant_invoke(self.state_machine.role)

        # --- API Gateway front door -----------------------------------------
        start_execution_fn = _lambda.Function(
            self, "StartScanApi",
            function_name="therascout-start-scan",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_inline(_START_EXECUTION_CODE),
            timeout=Duration.seconds(10),
            environment={"STATE_MACHINE_ARN": self.state_machine.state_machine_arn},
        )
        self.state_machine.grant_start_execution(start_execution_fn)

        api = apigw.LambdaRestApi(
            self, "TheraScoutApi",
            handler=start_execution_fn,
            proxy=False,
        )
        scan = api.root.add_resource("scan")
        scan.add_method("POST")


_START_EXECUTION_CODE = """
import json, os, uuid, boto3

sfn = boto3.client("stepfunctions")

def lambda_handler(event, context):
    body = json.loads(event.get("body") or "{}")
    therapeutic_area = body.get("therapeutic_area", "Colorectal Cancer")

    response = sfn.start_execution(
        stateMachineArn=os.environ["STATE_MACHINE_ARN"],
        name=f"scan-{uuid.uuid4()}",
        input=json.dumps({"therapeutic_area": therapeutic_area}),
    )
    return {
        "statusCode": 202,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"executionArn": response["executionArn"]}),
    }
"""
