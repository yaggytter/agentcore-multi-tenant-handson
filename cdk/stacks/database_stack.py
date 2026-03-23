"""
Database Stack for AgentCore Multi-Tenant Hands-on

Creates an Aurora Serverless v2 PostgreSQL cluster in the VPC
with a custom resource to initialize the schema with Row-Level Security (RLS)
for tenant isolation.
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
    custom_resources as cr,
)
from constructs import Construct


class DatabaseStack(Stack):
    """Aurora Serverless v2 PostgreSQL with RLS for tenant isolation."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        aurora_security_group: ec2.ISecurityGroup,
        lambda_security_group: ec2.ISecurityGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # -----------------------------------------------------------
        # Database credentials stored in Secrets Manager
        # -----------------------------------------------------------
        self.db_secret = rds.DatabaseSecret(
            self,
            "AuroraSecret",
            username="agentcore_admin",
            secret_name="agentcore/aurora/credentials",
        )

        # -----------------------------------------------------------
        # Aurora Serverless v2 PostgreSQL Cluster
        # Min capacity 0.5 ACU (cost-effective for hands-on)
        # Max capacity 4 ACU (sufficient for demo workloads)
        # -----------------------------------------------------------
        self.cluster = rds.DatabaseCluster(
            self,
            "AuroraCluster",
            cluster_identifier="agentcore-multi-tenant",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_6,
            ),
            credentials=rds.Credentials.from_secret(self.db_secret),
            default_database_name="agentcore",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ),
            security_groups=[aurora_security_group],
            serverless_v2_min_capacity=0.5,
            serverless_v2_max_capacity=4,
            writer=rds.ClusterInstance.serverless_v2(
                "Writer",
                auto_minor_version_upgrade=True,
            ),
            storage_encrypted=True,
            removal_policy=RemovalPolicy.DESTROY,  # Hands-on: easy cleanup
        )

        # -----------------------------------------------------------
        # Schema Initialization Lambda
        # Runs SQL to create tables with RLS policies for tenant
        # isolation. Executes once via a CloudFormation Custom Resource.
        # Uses Code.from_asset() to avoid the 4096-byte inline limit.
        # -----------------------------------------------------------
        schema_init_lambda = lambda_.Function(
            self,
            "SchemaInitLambda",
            function_name="agentcore-schema-init",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="handler.handler",
            code=lambda_.Code.from_asset("../lambda/schema_init"),
            timeout=Duration.minutes(5),
            memory_size=256,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            security_groups=[lambda_security_group],
            environment={
                "CLUSTER_ARN": self.cluster.cluster_arn,
                "SECRET_ARN": self.db_secret.secret_arn,
                "DATABASE_NAME": "agentcore",
            },
        )

        # Grant the Lambda access to the Aurora cluster and secret
        self.db_secret.grant_read(schema_init_lambda)
        schema_init_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "rds-data:ExecuteStatement",
                    "rds-data:BatchExecuteStatement",
                ],
                resources=[self.cluster.cluster_arn],
            )
        )

        # Enable Data API on the cluster for schema init Lambda
        cfn_cluster = self.cluster.node.default_child
        cfn_cluster.add_property_override("EnableHttpEndpoint", True)

        # -----------------------------------------------------------
        # cr.Provider handles CloudFormation callbacks automatically.
        # The Lambda just needs to return a dict with PhysicalResourceId.
        # -----------------------------------------------------------
        schema_init_provider = cr.Provider(
            self,
            "SchemaInitProvider",
            on_event_handler=schema_init_lambda,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # -----------------------------------------------------------
        # Custom Resource to trigger schema initialization
        # Runs after the cluster is ready
        # -----------------------------------------------------------
        from aws_cdk import CustomResource

        schema_init_resource = CustomResource(
            self,
            "SchemaInitResource",
            service_token=schema_init_provider.service_token,
            properties={
                # Change this value to force re-initialization
                "SchemaVersion": "2.0.0",
            },
        )
        schema_init_resource.node.add_dependency(self.cluster)

        # -----------------------------------------------------------
        # Outputs
        # -----------------------------------------------------------
        CfnOutput(
            self,
            "ClusterEndpoint",
            value=self.cluster.cluster_endpoint.hostname,
            description="Aurora cluster writer endpoint",
            export_name="AgentCoreDbEndpoint",
        )

        CfnOutput(
            self,
            "ClusterArn",
            value=self.cluster.cluster_arn,
            description="Aurora cluster ARN (for Data API)",
            export_name="AgentCoreDbClusterArn",
        )

        CfnOutput(
            self,
            "SecretArn",
            value=self.db_secret.secret_arn,
            description="Database credentials secret ARN",
            export_name="AgentCoreDbSecretArn",
        )

        CfnOutput(
            self,
            "DatabaseName",
            value="agentcore",
            description="Database name",
            export_name="AgentCoreDbName",
        )
