"""
Memory Stack for AgentCore Multi-Tenant Hands-on

Sets up AgentCore Memory with Short-Term Memory (STM) and
Long-Term Memory (LTM) namespaces for conversation state management.
Uses custom resources since CDK L2 constructs for AgentCore Memory
do not exist yet.
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    CustomResource,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs,
    custom_resources as cr,
)
from constructs import Construct


class MemoryStack(Stack):
    """AgentCore Memory configuration (STM + LTM namespaces)."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        runtime_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # -----------------------------------------------------------
        # Memory Custom Resource Lambda
        # Creates STM and LTM memory namespaces via the AgentCore API.
        #
        # STM (Short-Term Memory): Stores the current conversation
        #   context within a session. Scoped by tenant + session.
        #
        # LTM (Long-Term Memory): Stores persistent knowledge and
        #   preferences across sessions. Scoped by tenant + user.
        # -----------------------------------------------------------
        memory_cr_lambda = lambda_.Function(
            self,
            "MemoryCustomResourceLambda",
            function_name="agentcore-memory-cr",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                """
import json
import boto3

def handler(event, context):
    \"\"\"
    Custom Resource to create/delete AgentCore Memory namespaces.
    Creates both STM (session-scoped) and LTM (user-scoped) stores.
    Returns a dict -- cr.Provider handles the CloudFormation callback.
    \"\"\"
    props = event['ResourceProperties']
    request_type = event['RequestType']

    try:
        client = boto3.client('bedrock-agentcore')

        if request_type == 'Create':
            # Create Short-Term Memory namespace
            stm_response = client.create_memory(
                name=props['StmName'],
                description='Short-term conversation memory for active sessions',
                agentRuntimeId=props['RuntimeId'],
                memoryStrategies=[
                    {
                        'semanticMemoryStrategy': {
                            'name': 'stm-semantic',
                            'description': 'Semantic search over recent conversation turns',
                            'model': 'us.anthropic.claude-sonnet-4-6',
                            'namespaceConfiguration': {
                                'type': 'SESSION_SCOPED',
                            },
                        },
                    },
                    {
                        'summaryMemoryStrategy': {
                            'name': 'stm-summary',
                            'description': 'Rolling summary of conversation context',
                            'model': 'us.anthropic.claude-sonnet-4-6',
                            'namespaceConfiguration': {
                                'type': 'SESSION_SCOPED',
                            },
                        },
                    },
                ],
            )
            stm_id = stm_response['memoryId']

            # Create Long-Term Memory namespace
            ltm_response = client.create_memory(
                name=props['LtmName'],
                description='Long-term memory for user preferences and knowledge',
                agentRuntimeId=props['RuntimeId'],
                memoryStrategies=[
                    {
                        'semanticMemoryStrategy': {
                            'name': 'ltm-semantic',
                            'description': 'Persistent semantic memory across sessions',
                            'model': 'us.anthropic.claude-sonnet-4-6',
                            'namespaceConfiguration': {
                                'type': 'USER_SCOPED',
                            },
                        },
                    },
                    {
                        'userPreferenceMemoryStrategy': {
                            'name': 'ltm-preferences',
                            'description': 'Extracted user preferences and patterns',
                            'model': 'us.anthropic.claude-sonnet-4-6',
                            'namespaceConfiguration': {
                                'type': 'USER_SCOPED',
                            },
                        },
                    },
                ],
            )
            ltm_id = ltm_response['memoryId']

            physical_id = f"{stm_id}|{ltm_id}"
            return {
                'PhysicalResourceId': physical_id,
                'Data': {
                    'StmId': stm_id,
                    'LtmId': ltm_id,
                },
            }

        elif request_type == 'Update':
            # Memory namespaces are immutable; recreate if needed
            physical_id = event['PhysicalResourceId']
            return {
                'PhysicalResourceId': physical_id,
                'Data': {},
            }

        elif request_type == 'Delete':
            physical_id = event['PhysicalResourceId']
            try:
                ids = physical_id.split('|')
                for memory_id in ids:
                    try:
                        client.delete_memory(memoryId=memory_id)
                    except client.exceptions.ResourceNotFoundException:
                        pass
            except Exception as e:
                print(f"Delete error: {e}")
            return {
                'PhysicalResourceId': physical_id,
                'Data': {},
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        raise
"""
            ),
            timeout=Duration.minutes(5),
            memory_size=256,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # Grant permissions for AgentCore Memory API
        memory_cr_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:*",
                ],
                resources=["*"],
            )
        )

        # Use cr.Provider to handle CloudFormation callbacks
        memory_provider = cr.Provider(
            self,
            "MemoryProvider",
            on_event_handler=memory_cr_lambda,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # -----------------------------------------------------------
        # Create Memory namespaces via Custom Resource
        # -----------------------------------------------------------
        self.memory_resource = CustomResource(
            self,
            "AgentCoreMemory",
            service_token=memory_provider.service_token,
            properties={
                "RuntimeId": runtime_id,
                "StmName": "agentcore-mt-stm",
                "LtmName": "agentcore-mt-ltm",
                # Change to force recreation
                "Version": "1.0.0",
            },
        )

        self.stm_id = self.memory_resource.get_att_string("StmId")
        self.ltm_id = self.memory_resource.get_att_string("LtmId")

        # -----------------------------------------------------------
        # Outputs
        # -----------------------------------------------------------
        CfnOutput(
            self,
            "StmMemoryId",
            value=self.stm_id,
            description="Short-Term Memory namespace ID",
            export_name="AgentCoreStmId",
        )

        CfnOutput(
            self,
            "LtmMemoryId",
            value=self.ltm_id,
            description="Long-Term Memory namespace ID",
            export_name="AgentCoreLtmId",
        )
