"""
DataStack — the "Data layer" box from the architecture diagram.

Creates:
  - S3 bucket        : raw ingested data (WHO, PubMed, ClinicalTrials.gov, openFDA)
  - OpenSearch Serverless collection : vector store for RAG (Bedrock Knowledge Base target)
  - RDS PostgreSQL    : structured metadata (trial records, scoring history)

Sized deliberately for an MVP, not production:
  - RDS: db.t4g.micro, Single-AZ, no RDS Proxy, no Multi-AZ
  - OpenSearch: 1 Indexing OCU + 1 Search OCU (the practical minimum)
"""
from aws_cdk import (
    Stack, RemovalPolicy, Duration,
    aws_s3 as s3,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_opensearchserverless as aoss,
)
from constructs import Construct


class DataStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- S3: raw ingested data ---------------------------------------
        self.data_bucket = s3.Bucket(
            self, "RawDataBucket",
            bucket_name=None,  # let CDK generate a unique name
            removal_policy=RemovalPolicy.RETAIN,
            versioned=False,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="expire-staging-after-90-days",
                    prefix="staging/",
                    expiration=Duration.days(90),
                )
            ],
        )

        # --- Networking for RDS -------------------------------------------
        self.vpc = ec2.Vpc(
            self, "TheraScoutVpc",
            max_azs=2,
            nat_gateways=0,  # keep MVP cost down; agents call RDS via VPC endpoints/Lambda in VPC
        )

        # --- RDS PostgreSQL: structured metadata ---------------------------
        self.metadata_db = rds.DatabaseInstance(
            self, "MetadataDb",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO
            ),
            vpc=self.vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            allocated_storage=20,
            storage_type=rds.StorageType.GP3,
            multi_az=False,               # MVP: Single-AZ only
            deletion_protection=False,     # MVP: allow easy teardown
            removal_policy=RemovalPolicy.DESTROY,
            database_name="therascout",
            credentials=rds.Credentials.from_generated_secret("therascout_admin"),
        )

        # --- OpenSearch Serverless: vector store for RAG --------------------
        self.opensearch_collection = aoss.CfnCollection(
            self, "VectorCollection",
            name="therascout-vectors",
            type="VECTORSEARCH",
            description="RAG vector store for disease, research, trial and treatment embeddings",
        )

        # Minimal, permissive-for-MVP access policy — tighten before any real
        # enterprise data is connected.
        aoss.CfnAccessPolicy(
            self, "VectorCollectionAccessPolicy",
            name="therascout-vectors-access",
            type="data",
            policy=(
                '[{"Rules":[{"ResourceType":"collection",'
                '"Resource":["collection/therascout-vectors"],'
                '"Permission":["aoss:*"]},'
                '{"ResourceType":"index","Resource":["index/therascout-vectors/*"],'
                '"Permission":["aoss:*"]}],'
                '"Principal":["*"]}]'
            ),
        )
