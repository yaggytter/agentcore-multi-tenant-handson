#!/usr/bin/env python3
"""
CDK App Entry Point - AgentCore Multi-Tenant Hands-on

Orchestrates all stacks for a multi-tenant SaaS customer support agent
platform using Amazon Bedrock AgentCore, Aurora PostgreSQL, and Cognito.

Stack dependency graph:
    VpcStack ─────────────┐
    SupportingStack ──────┤
    CognitoStack ─────────┤
                          ├──> DatabaseStack
                          ├──> GatewayStack ──> RuntimeStack ──> MemoryStack
                          └──> ObservabilityStack
"""

import aws_cdk as cdk

from stacks.vpc_stack import VpcStack
from stacks.cognito_stack import CognitoStack
from stacks.database_stack import DatabaseStack
from stacks.supporting_stack import SupportingStack
from stacks.gateway_stack import GatewayStack
from stacks.runtime_stack import RuntimeStack
from stacks.memory_stack import MemoryStack
from stacks.observability_stack import ObservabilityStack


app = cdk.App()

# Common environment (uses CLI-configured account and region)
env = cdk.Environment(
    account=app.node.try_get_context("account") or None,
    region=app.node.try_get_context("region") or None,
)
env_kwargs = {"env": env} if env.account else {}

# -----------------------------------------------------------
# Foundation stacks (no cross-stack dependencies)
# -----------------------------------------------------------

vpc_stack = VpcStack(
    app,
    "AgentCoreVpcStack",
    description="VPC with public/private subnets for AgentCore multi-tenant platform",
    **env_kwargs,
)

supporting_stack = SupportingStack(
    app,
    "AgentCoreSupportingStack",
    description="ECR, S3, IAM roles for AgentCore multi-tenant platform",
    **env_kwargs,
)

cognito_stack = CognitoStack(
    app,
    "AgentCoreCognitoStack",
    description="Cognito User Pool with multi-tenant attributes and triggers",
    **env_kwargs,
)

# -----------------------------------------------------------
# Database stack (depends on VPC)
# -----------------------------------------------------------

database_stack = DatabaseStack(
    app,
    "AgentCoreDatabaseStack",
    vpc=vpc_stack.vpc,
    aurora_security_group=vpc_stack.aurora_security_group,
    lambda_security_group=vpc_stack.lambda_security_group,
    description="Aurora Serverless v2 PostgreSQL with RLS for tenant isolation",
    **env_kwargs,
)
database_stack.add_dependency(vpc_stack)

# -----------------------------------------------------------
# Gateway stack (depends on VPC, Database, Cognito, Supporting)
# -----------------------------------------------------------

gateway_stack = GatewayStack(
    app,
    "AgentCoreGatewayStack",
    vpc=vpc_stack.vpc,
    lambda_security_group=vpc_stack.lambda_security_group,
    db_cluster_arn=database_stack.cluster.cluster_arn,
    db_secret_arn=database_stack.db_secret.secret_arn,
    user_pool_id=cognito_stack.user_pool.user_pool_id,
    user_pool_client_id=cognito_stack.user_pool_client.user_pool_client_id,
    service_role_arn=supporting_stack.agentcore_service_role.role_arn,
    description="AgentCore Gateway with tool Lambda targets and interceptor",
    **env_kwargs,
)
gateway_stack.add_dependency(vpc_stack)
gateway_stack.add_dependency(database_stack)
gateway_stack.add_dependency(cognito_stack)
gateway_stack.add_dependency(supporting_stack)

# -----------------------------------------------------------
# Runtime stack (depends on Gateway, Supporting, Cognito, Database)
# -----------------------------------------------------------

runtime_stack = RuntimeStack(
    app,
    "AgentCoreRuntimeStack",
    ecr_repository_uri=supporting_stack.ecr_repository.repository_uri,
    runtime_execution_role_arn=supporting_stack.runtime_execution_role.role_arn,
    service_role_arn=supporting_stack.agentcore_service_role.role_arn,
    gateway_id=gateway_stack.gateway_id,
    db_cluster_arn=database_stack.cluster.cluster_arn,
    db_secret_arn=database_stack.db_secret.secret_arn,
    user_pool_id=cognito_stack.user_pool.user_pool_id,
    user_pool_client_id=cognito_stack.user_pool_client.user_pool_client_id,
    description="AgentCore Runtime with container image and OAuth configuration",
    **env_kwargs,
)
runtime_stack.add_dependency(gateway_stack)
runtime_stack.add_dependency(supporting_stack)
runtime_stack.add_dependency(cognito_stack)
runtime_stack.add_dependency(database_stack)

# -----------------------------------------------------------
# Memory stack (depends on Runtime)
# -----------------------------------------------------------

memory_stack = MemoryStack(
    app,
    "AgentCoreMemoryStack",
    runtime_id=runtime_stack.runtime_id,
    description="AgentCore Memory with STM and LTM namespaces",
    **env_kwargs,
)
memory_stack.add_dependency(runtime_stack)

# -----------------------------------------------------------
# Observability stack (depends on Gateway, Runtime)
# -----------------------------------------------------------

observability_stack = ObservabilityStack(
    app,
    "AgentCoreObservabilityStack",
    gateway_id=gateway_stack.gateway_id,
    runtime_id=runtime_stack.runtime_id,
    description="CloudWatch dashboard, alarms, and log groups for AgentCore",
    **env_kwargs,
)
observability_stack.add_dependency(gateway_stack)
observability_stack.add_dependency(runtime_stack)

# -----------------------------------------------------------
# Synthesize
# -----------------------------------------------------------
app.synth()
