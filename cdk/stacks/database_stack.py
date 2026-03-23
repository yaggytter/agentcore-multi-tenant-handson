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
    CustomResource,
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
        # -----------------------------------------------------------
        schema_init_lambda = lambda_.Function(
            self,
            "SchemaInitLambda",
            function_name="agentcore-schema-init",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                """
import json
import boto3
import cfnresponse
import os

def handler(event, context):
    \"\"\"
    Custom Resource handler to initialize Aurora PostgreSQL schema
    with Row-Level Security (RLS) for multi-tenant isolation.
    \"\"\"
    if event['RequestType'] == 'Delete':
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        return

    try:
        rds_client = boto3.client('rds-data')
        cluster_arn = os.environ['CLUSTER_ARN']
        secret_arn = os.environ['SECRET_ARN']
        database = os.environ['DATABASE_NAME']

        # SQL statements to create schema with RLS
        statements = [
            # Tenants table
            \"\"\"
            CREATE TABLE IF NOT EXISTS tenants (
                tenant_id VARCHAR(64) PRIMARY KEY,
                tenant_name VARCHAR(256) NOT NULL,
                plan_tier VARCHAR(32) NOT NULL DEFAULT 'standard',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            \"\"\",

            # Support tickets table with tenant_id for RLS
            \"\"\"
            CREATE TABLE IF NOT EXISTS support_tickets (
                ticket_id SERIAL PRIMARY KEY,
                tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
                title VARCHAR(512) NOT NULL,
                description TEXT,
                status VARCHAR(32) NOT NULL DEFAULT 'open',
                priority VARCHAR(16) NOT NULL DEFAULT 'medium',
                assigned_agent VARCHAR(256),
                created_by VARCHAR(256) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            \"\"\",

            # Knowledge base articles with tenant scope
            \"\"\"
            CREATE TABLE IF NOT EXISTS knowledge_articles (
                article_id SERIAL PRIMARY KEY,
                tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
                title VARCHAR(512) NOT NULL,
                content TEXT NOT NULL,
                category VARCHAR(128),
                tags TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            \"\"\",

            # Billing records with tenant scope
            \"\"\"
            CREATE TABLE IF NOT EXISTS billing_records (
                record_id SERIAL PRIMARY KEY,
                tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
                invoice_number VARCHAR(64),
                amount DECIMAL(10,2) NOT NULL,
                currency VARCHAR(3) NOT NULL DEFAULT 'USD',
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                billing_period_start DATE,
                billing_period_end DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            \"\"\",

            # Agent conversation history
            \"\"\"
            CREATE TABLE IF NOT EXISTS conversation_history (
                conversation_id SERIAL PRIMARY KEY,
                tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(tenant_id),
                session_id VARCHAR(128) NOT NULL,
                user_id VARCHAR(256) NOT NULL,
                role VARCHAR(16) NOT NULL,
                content TEXT NOT NULL,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            \"\"\",

            # Enable RLS on all tenant-scoped tables
            \"ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;\",
            \"ALTER TABLE knowledge_articles ENABLE ROW LEVEL SECURITY;\",
            \"ALTER TABLE billing_records ENABLE ROW LEVEL SECURITY;\",
            \"ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;\",

            # Create application role for tenant-scoped access
            \"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN CREATE ROLE app_user; END IF; END $$;\",

            # RLS policies: each tenant can only see their own data
            \"DROP POLICY IF EXISTS tenant_isolation_tickets ON support_tickets;\",
            \"\"\"
            CREATE POLICY tenant_isolation_tickets ON support_tickets
                FOR ALL
                USING (tenant_id = current_setting('app.current_tenant_id', true))
                WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
            \"\"\",

            \"DROP POLICY IF EXISTS tenant_isolation_articles ON knowledge_articles;\",
            \"\"\"
            CREATE POLICY tenant_isolation_articles ON knowledge_articles
                FOR ALL
                USING (tenant_id = current_setting('app.current_tenant_id', true))
                WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
            \"\"\",

            \"DROP POLICY IF EXISTS tenant_isolation_billing ON billing_records;\",
            \"\"\"
            CREATE POLICY tenant_isolation_billing ON billing_records
                FOR ALL
                USING (tenant_id = current_setting('app.current_tenant_id', true))
                WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
            \"\"\",

            \"DROP POLICY IF EXISTS tenant_isolation_conversations ON conversation_history;\",
            \"\"\"
            CREATE POLICY tenant_isolation_conversations ON conversation_history
                FOR ALL
                USING (tenant_id = current_setting('app.current_tenant_id', true))
                WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
            \"\"\",

            # Grant permissions to app_user role
            \"GRANT SELECT, INSERT, UPDATE, DELETE ON support_tickets TO app_user;\",
            \"GRANT SELECT, INSERT, UPDATE, DELETE ON knowledge_articles TO app_user;\",
            \"GRANT SELECT, INSERT, UPDATE, DELETE ON billing_records TO app_user;\",
            \"GRANT SELECT, INSERT, UPDATE, DELETE ON conversation_history TO app_user;\",
            \"GRANT SELECT ON tenants TO app_user;\",
            \"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;\",

            # Create indexes for tenant_id lookups
            \"CREATE INDEX IF NOT EXISTS idx_tickets_tenant ON support_tickets(tenant_id);\",
            \"CREATE INDEX IF NOT EXISTS idx_articles_tenant ON knowledge_articles(tenant_id);\",
            \"CREATE INDEX IF NOT EXISTS idx_billing_tenant ON billing_records(tenant_id);\",
            \"CREATE INDEX IF NOT EXISTS idx_conversations_tenant ON conversation_history(tenant_id);\",

            # Seed demo tenants
            \"\"\"
            INSERT INTO tenants (tenant_id, tenant_name, plan_tier)
            VALUES
                ('tenant-a', 'Acme Corporation', 'enterprise'),
                ('tenant-b', 'Beta Industries', 'standard')
            ON CONFLICT (tenant_id) DO NOTHING;
            \"\"\",
        ]

        for sql in statements:
            rds_client.execute_statement(
                resourceArn=cluster_arn,
                secretArn=secret_arn,
                database=database,
                sql=sql.strip(),
            )

        cfnresponse.send(event, context, cfnresponse.SUCCESS, {
            'Message': 'Schema initialized successfully'
        })
    except Exception as e:
        print(f"Error: {str(e)}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {
            'Error': str(e)
        })
"""
            ),
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
        # Custom Resource to trigger schema initialization
        # Runs after the cluster is ready
        # -----------------------------------------------------------
        schema_init_resource = CustomResource(
            self,
            "SchemaInitResource",
            service_token=schema_init_lambda.function_arn,
            properties={
                # Change this value to force re-initialization
                "SchemaVersion": "1.0.0",
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
