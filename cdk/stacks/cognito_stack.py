"""
Cognito Stack for AgentCore Multi-Tenant Hands-on

Creates a Cognito User Pool with custom tenant attributes,
Pre-Token Generation Lambda trigger for injecting tenant context,
and user groups for each tenant.
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_cognito as cognito,
    aws_lambda as lambda_,
    aws_logs as logs,
)
from constructs import Construct


class CognitoStack(Stack):
    """Cognito User Pool for multi-tenant authentication."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # -----------------------------------------------------------
        # Pre-Token Generation Lambda Trigger
        # Injects custom:tenantId into the JWT token claims
        # so downstream services can enforce tenant isolation.
        # -----------------------------------------------------------
        pre_token_lambda = lambda_.Function(
            self,
            "PreTokenGenerationLambda",
            function_name="agentcore-pre-token-generation",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                """
import json

def handler(event, context):
    \"\"\"
    Pre-Token Generation trigger.
    Copies custom:tenantId into the access token claims
    so that AgentCore interceptor can extract tenant context.
    \"\"\"
    tenant_id = event['request']['userAttributes'].get('custom:tenantId', '')
    group_config = event.get('response', {}).get('claimsOverrideDetails', {})

    event['response'] = {
        'claimsOverrideDetails': {
            'claimsToAddOrOverride': {
                'custom:tenantId': tenant_id,
            },
        },
    }
    print(f"Pre-token generation: tenantId={tenant_id}, user={event['userName']}")
    return event
"""
            ),
            timeout=Duration.seconds(10),
            memory_size=128,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # -----------------------------------------------------------
        # Cognito User Pool
        # custom:tenantId attribute binds each user to a tenant
        # -----------------------------------------------------------
        self.user_pool = cognito.UserPool(
            self,
            "AgentCoreUserPool",
            user_pool_name="agentcore-multi-tenant-pool",
            self_sign_up_enabled=False,  # Admin creates users for hands-on
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=True,
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
            ),
            custom_attributes={
                "tenantId": cognito.StringAttribute(
                    min_len=1,
                    max_len=64,
                    mutable=False,  # Tenant binding is immutable
                ),
            },
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY,  # Hands-on: easy cleanup
            lambda_triggers=cognito.UserPoolTriggers(
                pre_token_generation=pre_token_lambda,
            ),
        )

        # -----------------------------------------------------------
        # App Client for the SaaS application
        # Supports USER_PASSWORD_AUTH for hands-on simplicity
        # -----------------------------------------------------------
        self.user_pool_client = self.user_pool.add_client(
            "AgentCoreAppClient",
            user_pool_client_name="agentcore-app-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,  # For hands-on CLI testing
                user_srp=True,
            ),
            generate_secret=False,  # Public client for hands-on
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(7),
        )

        # -----------------------------------------------------------
        # Resource Server for OAuth2 scopes (API authorization)
        # -----------------------------------------------------------
        resource_server = self.user_pool.add_resource_server(
            "AgentCoreResourceServer",
            identifier="agentcore-api",
            scopes=[
                cognito.ResourceServerScope(
                    scope_name="agent.invoke",
                    scope_description="Invoke agent operations",
                ),
                cognito.ResourceServerScope(
                    scope_name="tickets.read",
                    scope_description="Read support tickets",
                ),
                cognito.ResourceServerScope(
                    scope_name="tickets.write",
                    scope_description="Create and update support tickets",
                ),
            ],
        )

        # -----------------------------------------------------------
        # User Groups for tenant isolation demonstration
        # -----------------------------------------------------------
        tenant_a_group = cognito.CfnUserPoolGroup(
            self,
            "TenantAGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="tenant-a",
            description="Users belonging to Tenant A",
        )

        tenant_b_group = cognito.CfnUserPoolGroup(
            self,
            "TenantBGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="tenant-b",
            description="Users belonging to Tenant B",
        )

        # -----------------------------------------------------------
        # Outputs
        # -----------------------------------------------------------
        CfnOutput(
            self,
            "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID",
            export_name="AgentCoreUserPoolId",
        )

        CfnOutput(
            self,
            "UserPoolArn",
            value=self.user_pool.user_pool_arn,
            description="Cognito User Pool ARN",
            export_name="AgentCoreUserPoolArn",
        )

        CfnOutput(
            self,
            "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito App Client ID",
            export_name="AgentCoreUserPoolClientId",
        )
