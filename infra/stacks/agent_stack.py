"""
AgentStack — the Lambda "tool boxes" from the pipeline diagram.

Each of these Lambdas is a tool that exactly one agent is allowed to call.
They are deliberately kept separate (one function per tool) rather than
one monolithic Lambda, so IAM permissions and the AgentCore Gateway tool
registration stay 1:1 with the pipeline diagram.
"""
from aws_cdk import (
    Stack, Duration,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3 as s3,
    aws_rds as rds,
)
from constructs import Construct


class AgentStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str,
        data_bucket: s3.Bucket, metadata_db: rds.DatabaseInstance,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.tool_functions = {}

        common_env = {
            "DATA_BUCKET_NAME": data_bucket.bucket_name,
        }

        def make_tool(name: str, code_dir: str, timeout_sec: int = 30, extra_env: dict | None = None):
            fn = _lambda.Function(
                self, name,
                function_name=f"therascout-{name}",
                runtime=_lambda.Runtime.PYTHON_3_12,
                handler="handler.lambda_handler",
                code=_lambda.Code.from_asset(f"../tools/{code_dir}"),
                timeout=Duration.seconds(timeout_sec),
                memory_size=256,
                environment={**common_env, **(extra_env or {})},
            )
            data_bucket.grant_read_write(fn)
            self.tool_functions[name] = fn
            return fn

        # --- Data-retrieval tools, one per specialist agent -----------------
        make_tool("query_globocan_data", "query_globocan_data")
        make_tool("query_pubmed", "query_pubmed")
        make_tool("query_clinicaltrials", "query_clinicaltrials")
        make_tool("query_openfda", "query_openfda")

        # --- Ingest decision logic -----------------------------------------
        make_tool("check_data_scope", "check_data_scope", timeout_sec=10)

        # --- Mocked enterprise data source (the "no" branch) -----------------
        make_tool("enrich_enterprise_data", "enrich_enterprise_data", timeout_sec=10)

        # --- Bridge Lambda: Step Functions -> AgentCore Runtime (used for
        #     the gap_scoring and orchestrator agents that need real LLM
        #     reasoning, as opposed to the pure data-fetch tools above) -----
        agentcore_fn = make_tool("invoke_agentcore_agent", "invoke_agentcore_agent", timeout_sec=90)
        agentcore_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock-agentcore:InvokeAgentRuntime"],
                resources=["*"],
            )
        )

        # --- Report composer (needs RDS access + longer timeout for PDF gen) --
        # NOTE: compose_pdf_report/requirements.txt (reportlab) is not
        # installed by a plain `Code.from_asset` call. Before deploying,
        # either (a) run `pip install -r requirements.txt -t .` inside
        # tools/compose_pdf_report/ so the dependency is bundled into the
        # zip, or (b) switch this to `_lambda.Code.from_asset(..., bundling=...)`
        # with a Docker-based bundling step. Left as a manual step here so
        # the build order stays visible rather than hidden behind CDK magic.
        report_fn = make_tool(
            "compose_pdf_report", "compose_pdf_report",
            timeout_sec=60,
            extra_env={"DB_SECRET_ARN": metadata_db.secret.secret_arn if metadata_db.secret else ""},
        )
        if metadata_db.secret:
            metadata_db.secret.grant_read(report_fn)
        metadata_db.connections.allow_default_port_from(report_fn)

        # --- Bedrock invocation permission, shared by every tool that needs
        #     to call the model directly (most tools just fetch data; the
        #     agents themselves call Bedrock via AgentCore, not via these
        #     Lambdas — this permission is here for the ones that don't) ----
        bedrock_policy = iam.PolicyStatement(
            actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            resources=["*"],
        )
        for fn in self.tool_functions.values():
            fn.add_to_role_policy(bedrock_policy)
