"""
Supporting Stack for AgentCore Multi-Tenant Hands-on

Creates shared infrastructure resources: ECR repository for the agent
container image, S3 bucket for artifacts, and IAM roles used by
AgentCore Gateway and Runtime.
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    RemovalPolicy,
    aws_ecr as ecr,
    aws_s3 as s3,
    aws_iam as iam,
)
from constructs import Construct


class SupportingStack(Stack):
    """Shared infrastructure: ECR, S3, IAM roles for AgentCore."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # -----------------------------------------------------------
        # ECR Repository for the agent container image
        # The agent runtime container is pushed here and referenced
        # by the AgentCore Runtime configuration.
        # -----------------------------------------------------------
        self.ecr_repository = ecr.Repository(
            self,
            "AgentImageRepo",
            repository_name="agentcore-multi-tenant-agent",
            removal_policy=RemovalPolicy.DESTROY,
            empty_on_delete=True,
            image_scan_on_push=True,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep only last 10 images",
                    max_image_count=10,
                )
            ],
        )

        # -----------------------------------------------------------
        # S3 Bucket for agent artifacts (prompts, configs, etc.)
        # -----------------------------------------------------------
        self.artifacts_bucket = s3.Bucket(
            self,
            "ArtifactsBucket",
            bucket_name=None,  # Auto-generated unique name
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
        )

        # -----------------------------------------------------------
        # IAM Role for AgentCore Gateway Lambda tools
        # Assumed by tool Lambda functions invoked via the Gateway.
        # -----------------------------------------------------------
        self.gateway_tool_role = iam.Role(
            self,
            "GatewayToolRole",
            role_name="agentcore-gateway-tool-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                ),
            ],
        )

        # -----------------------------------------------------------
        # IAM Role for AgentCore Runtime execution
        # Grants permissions the agent needs at runtime: Bedrock model
        # invocation, Secrets Manager access, S3 artifact reads, etc.
        # -----------------------------------------------------------
        self.runtime_execution_role = iam.Role(
            self,
            "RuntimeExecutionRole",
            role_name="agentcore-runtime-execution-role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("bedrock.amazonaws.com"),
                iam.ServicePrincipal("lambda.amazonaws.com"),
            ),
            inline_policies={
                "BedrockAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="InvokeModels",
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream",
                            ],
                            resources=["*"],
                        ),
                    ]
                ),
                "SecretsManagerAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="ReadSecrets",
                            actions=[
                                "secretsmanager:GetSecretValue",
                            ],
                            resources=[
                                f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:agentcore/*"
                            ],
                        ),
                    ]
                ),
                "S3ArtifactAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="ReadArtifacts",
                            actions=[
                                "s3:GetObject",
                                "s3:ListBucket",
                            ],
                            resources=[
                                self.artifacts_bucket.bucket_arn,
                                f"{self.artifacts_bucket.bucket_arn}/*",
                            ],
                        ),
                    ]
                ),
            },
        )

        # -----------------------------------------------------------
        # IAM Role for AgentCore service integration
        # Used by AgentCore to manage resources on behalf of the user.
        # -----------------------------------------------------------
        self.agentcore_service_role = iam.Role(
            self,
            "AgentCoreServiceRole",
            role_name="agentcore-service-role",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            inline_policies={
                "AgentCorePermissions": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="LambdaInvoke",
                            actions=["lambda:InvokeFunction"],
                            resources=[
                                f"arn:aws:lambda:{self.region}:{self.account}:function:agentcore-*"
                            ],
                        ),
                        iam.PolicyStatement(
                            sid="ECRPull",
                            actions=[
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:BatchGetImage",
                                "ecr:BatchCheckLayerAvailability",
                            ],
                            resources=[self.ecr_repository.repository_arn],
                        ),
                        iam.PolicyStatement(
                            sid="ECRAuth",
                            actions=["ecr:GetAuthorizationToken"],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            sid="CloudWatchLogs",
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents",
                            ],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/agentcore/*"
                            ],
                        ),
                    ]
                ),
            },
        )

        # -----------------------------------------------------------
        # Outputs
        # -----------------------------------------------------------
        CfnOutput(
            self,
            "EcrRepositoryUri",
            value=self.ecr_repository.repository_uri,
            description="ECR repository URI for agent container image",
            export_name="AgentCoreEcrRepoUri",
        )

        CfnOutput(
            self,
            "ArtifactsBucketName",
            value=self.artifacts_bucket.bucket_name,
            description="S3 bucket for agent artifacts",
            export_name="AgentCoreArtifactsBucket",
        )

        CfnOutput(
            self,
            "RuntimeExecutionRoleArn",
            value=self.runtime_execution_role.role_arn,
            description="IAM role ARN for AgentCore Runtime",
            export_name="AgentCoreRuntimeRoleArn",
        )

        CfnOutput(
            self,
            "AgentCoreServiceRoleArn",
            value=self.agentcore_service_role.role_arn,
            description="IAM role ARN for AgentCore service",
            export_name="AgentCoreServiceRoleArn",
        )
