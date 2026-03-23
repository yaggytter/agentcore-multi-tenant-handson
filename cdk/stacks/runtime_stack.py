"""
Runtime Stack for AgentCore Multi-Tenant Hands-on

Configures the AgentCore Runtime with the agent container image,
OAuth configuration for Cognito, and environment variables for
database access. Uses custom resources since CDK L2 constructs
for AgentCore Runtime do not exist yet.
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    CustomResource,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct


class RuntimeStack(Stack):
    """AgentCore Runtime configuration for the multi-tenant agent."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        ecr_repository_uri: str,
        runtime_execution_role_arn: str,
        service_role_arn: str,
        gateway_id: str,
        db_cluster_arn: str,
        db_secret_arn: str,
        user_pool_id: str,
        user_pool_client_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # -----------------------------------------------------------
        # AgentCore Runtime Custom Resource Lambda
        # Creates the Runtime configuration via the AgentCore API.
        # The Runtime defines how the agent container is deployed
        # and what environment it receives.
        # -----------------------------------------------------------
        runtime_cr_lambda = lambda_.Function(
            self,
            "RuntimeCustomResourceLambda",
            function_name="agentcore-runtime-cr",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                """
import json
import boto3
import cfnresponse

def handler(event, context):
    \"\"\"
    Custom Resource to create/update/delete an AgentCore Runtime.
    The Runtime configures the agent container image, scaling,
    environment variables, and OAuth settings.
    \"\"\"
    props = event['ResourceProperties']
    request_type = event['RequestType']

    try:
        client = boto3.client('bedrock-agentcore')

        if request_type == 'Create':
            # Create the agent runtime with container configuration
            response = client.create_agent_runtime(
                agentRuntimeName=props['RuntimeName'],
                description=props.get('Description', ''),
                roleArn=props['RoleArn'],
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'containerUri': props['ContainerUri'],
                    },
                },
                networkConfiguration={
                    'networkMode': 'PUBLIC',
                },
                protocolConfiguration={
                    'serverProtocol': 'MCP',
                },
                environmentVariables={
                    'CLUSTER_ARN': props['ClusterArn'],
                    'SECRET_ARN': props['SecretArn'],
                    'DATABASE_NAME': props['DatabaseName'],
                    'GATEWAY_ID': props['GatewayId'],
                    'COGNITO_USER_POOL_ID': props['UserPoolId'],
                    'COGNITO_CLIENT_ID': props['UserPoolClientId'],
                    'AWS_REGION_NAME': props['RegionName'],
                },
                authorizationConfiguration={
                    'authorizationType': 'CUSTOM_JWT',
                    'customJWTAuthorizationConfiguration': {
                        'discoveryUrl': props['DiscoveryUrl'],
                        'allowedAudiences': [props['AllowedAudience']],
                        'allowedClients': [props['AllowedClient']],
                    },
                },
            )
            runtime_id = response['agentRuntimeId']
            runtime_endpoint = response.get('agentRuntimeEndpoint', '')
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                'RuntimeId': runtime_id,
                'RuntimeEndpoint': runtime_endpoint,
            }, runtime_id)

        elif request_type == 'Update':
            runtime_id = event['PhysicalResourceId']
            client.update_agent_runtime(
                agentRuntimeId=runtime_id,
                agentRuntimeName=props['RuntimeName'],
                description=props.get('Description', ''),
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'containerUri': props['ContainerUri'],
                    },
                },
                environmentVariables={
                    'CLUSTER_ARN': props['ClusterArn'],
                    'SECRET_ARN': props['SecretArn'],
                    'DATABASE_NAME': props['DatabaseName'],
                    'GATEWAY_ID': props['GatewayId'],
                    'COGNITO_USER_POOL_ID': props['UserPoolId'],
                    'COGNITO_CLIENT_ID': props['UserPoolClientId'],
                    'AWS_REGION_NAME': props['RegionName'],
                },
            )
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                'RuntimeId': runtime_id,
            }, runtime_id)

        elif request_type == 'Delete':
            runtime_id = event['PhysicalResourceId']
            try:
                client.delete_agent_runtime(agentRuntimeId=runtime_id)
            except client.exceptions.ResourceNotFoundException:
                pass
            except Exception as e:
                print(f"Delete error (may already be deleted): {e}")
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, runtime_id)

    except Exception as e:
        print(f"Error: {str(e)}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': str(e)})
"""
            ),
            timeout=Duration.minutes(10),
            memory_size=256,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # Grant the CR Lambda permissions to manage AgentCore Runtimes
        runtime_cr_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:*",
                    "iam:PassRole",
                ],
                resources=["*"],
            )
        )

        # Cognito discovery URL for OAuth configuration
        discovery_url = (
            f"https://cognito-idp.{self.region}.amazonaws.com/"
            f"{user_pool_id}/.well-known/openid-configuration"
        )

        # Container image tag (latest by default; override via context)
        image_tag = self.node.try_get_context("image_tag") or "latest"
        container_uri = f"{ecr_repository_uri}:{image_tag}"

        # -----------------------------------------------------------
        # Create the AgentCore Runtime
        # -----------------------------------------------------------
        self.runtime_resource = CustomResource(
            self,
            "AgentCoreRuntime",
            service_token=runtime_cr_lambda.function_arn,
            properties={
                "RuntimeName": "agentcore-multi-tenant-runtime",
                "Description": "Multi-tenant customer support agent runtime",
                "RoleArn": runtime_execution_role_arn,
                "ContainerUri": container_uri,
                "ClusterArn": db_cluster_arn,
                "SecretArn": db_secret_arn,
                "DatabaseName": "agentcore",
                "GatewayId": gateway_id,
                "UserPoolId": user_pool_id,
                "UserPoolClientId": user_pool_client_id,
                "RegionName": self.region,
                "DiscoveryUrl": discovery_url,
                "AllowedAudience": user_pool_client_id,
                "AllowedClient": user_pool_client_id,
                # Change this to force redeployment
                "Version": "1.0.0",
            },
        )

        self.runtime_id = self.runtime_resource.get_att_string("RuntimeId")
        self.runtime_endpoint = self.runtime_resource.get_att_string("RuntimeEndpoint")

        # -----------------------------------------------------------
        # Outputs
        # -----------------------------------------------------------
        CfnOutput(
            self,
            "RuntimeId",
            value=self.runtime_id,
            description="AgentCore Runtime ID",
            export_name="AgentCoreRuntimeId",
        )

        CfnOutput(
            self,
            "RuntimeEndpoint",
            value=self.runtime_endpoint,
            description="AgentCore Runtime endpoint URL",
            export_name="AgentCoreRuntimeEndpoint",
        )

        CfnOutput(
            self,
            "ContainerUri",
            value=container_uri,
            description="Agent container image URI",
            export_name="AgentCoreContainerUri",
        )
