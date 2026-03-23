"""
Gateway Stack for AgentCore Multi-Tenant Hands-on

Creates the AgentCore Gateway with Lambda tool targets for customer support
operations (ticket management, knowledge search, billing inquiry) and an
interceptor Lambda for multi-tenant request routing.

Uses boto3 custom resources since CDK L2 constructs for AgentCore
Gateway do not exist yet.
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    CustomResource,
    aws_ec2 as ec2,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_logs as logs,
    custom_resources as cr,
)
from constructs import Construct


class GatewayStack(Stack):
    """AgentCore Gateway with tool Lambda targets and interceptor."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        lambda_security_group: ec2.ISecurityGroup,
        db_cluster_arn: str,
        db_secret_arn: str,
        user_pool_arn: str,
        service_role_arn: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # -----------------------------------------------------------
        # Shared Lambda layer for database access utilities
        # (In a real project this would be a proper layer; inline for hands-on)
        # -----------------------------------------------------------

        # Common environment variables for tool Lambdas
        tool_env = {
            "CLUSTER_ARN": db_cluster_arn,
            "SECRET_ARN": db_secret_arn,
            "DATABASE_NAME": "agentcore",
        }

        # Common IAM policy for RDS Data API access
        rds_data_policy = iam.PolicyStatement(
            actions=[
                "rds-data:ExecuteStatement",
                "rds-data:BatchExecuteStatement",
            ],
            resources=[db_cluster_arn],
        )

        secrets_policy = iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[db_secret_arn],
        )

        # -----------------------------------------------------------
        # Tool Lambda: Ticket Management
        # Handles CRUD operations on support tickets, scoped by tenant.
        # -----------------------------------------------------------
        self.ticket_management_lambda = lambda_.Function(
            self,
            "TicketManagementLambda",
            function_name="agentcore-tool-ticket-management",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                """
import json
import boto3
import os

rds_client = boto3.client('rds-data')
CLUSTER_ARN = os.environ['CLUSTER_ARN']
SECRET_ARN = os.environ['SECRET_ARN']
DATABASE = os.environ['DATABASE_NAME']

def execute_sql(sql, params=None):
    kwargs = {
        'resourceArn': CLUSTER_ARN,
        'secretArn': SECRET_ARN,
        'database': DATABASE,
        'sql': sql,
    }
    if params:
        kwargs['parameters'] = params
    return rds_client.execute_statement(**kwargs)

def handler(event, context):
    \"\"\"
    Ticket management tool for AgentCore Gateway.
    Operations: list_tickets, get_ticket, create_ticket, update_ticket
    Tenant isolation enforced via RLS (SET app.current_tenant_id).
    \"\"\"
    tenant_id = event.get('tenant_id', '')
    action = event.get('action', 'list_tickets')

    # Set tenant context for RLS
    execute_sql(f"SET app.current_tenant_id = '{tenant_id}'")

    if action == 'list_tickets':
        status_filter = event.get('status', None)
        sql = "SELECT * FROM support_tickets"
        if status_filter:
            sql += f" WHERE status = '{status_filter}'"
        sql += " ORDER BY created_at DESC LIMIT 50"
        result = execute_sql(sql)
        return {'statusCode': 200, 'body': json.dumps({'tickets': str(result.get('records', []))})}

    elif action == 'get_ticket':
        ticket_id = event.get('ticket_id')
        result = execute_sql(
            "SELECT * FROM support_tickets WHERE ticket_id = :id",
            [{'name': 'id', 'value': {'longValue': int(ticket_id)}}]
        )
        return {'statusCode': 200, 'body': json.dumps({'ticket': str(result.get('records', []))})}

    elif action == 'create_ticket':
        result = execute_sql(
            \"\"\"INSERT INTO support_tickets (tenant_id, title, description, priority, created_by)
               VALUES (:tenant, :title, :desc, :priority, :user) RETURNING ticket_id\"\"\",
            [
                {'name': 'tenant', 'value': {'stringValue': tenant_id}},
                {'name': 'title', 'value': {'stringValue': event.get('title', '')}},
                {'name': 'desc', 'value': {'stringValue': event.get('description', '')}},
                {'name': 'priority', 'value': {'stringValue': event.get('priority', 'medium')}},
                {'name': 'user', 'value': {'stringValue': event.get('user_id', 'unknown')}},
            ]
        )
        return {'statusCode': 201, 'body': json.dumps({'message': 'Ticket created', 'result': str(result)})}

    elif action == 'update_ticket':
        ticket_id = event.get('ticket_id')
        status = event.get('status', 'open')
        execute_sql(
            "UPDATE support_tickets SET status = :status, updated_at = CURRENT_TIMESTAMP WHERE ticket_id = :id",
            [
                {'name': 'status', 'value': {'stringValue': status}},
                {'name': 'id', 'value': {'longValue': int(ticket_id)}},
            ]
        )
        return {'statusCode': 200, 'body': json.dumps({'message': f'Ticket {ticket_id} updated to {status}'})}

    return {'statusCode': 400, 'body': json.dumps({'error': f'Unknown action: {action}'})}
"""
            ),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=tool_env,
        )
        self.ticket_management_lambda.add_to_role_policy(rds_data_policy)
        self.ticket_management_lambda.add_to_role_policy(secrets_policy)

        # -----------------------------------------------------------
        # Tool Lambda: Knowledge Search
        # Searches knowledge base articles scoped to the tenant.
        # -----------------------------------------------------------
        self.knowledge_search_lambda = lambda_.Function(
            self,
            "KnowledgeSearchLambda",
            function_name="agentcore-tool-knowledge-search",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                """
import json
import boto3
import os

rds_client = boto3.client('rds-data')
CLUSTER_ARN = os.environ['CLUSTER_ARN']
SECRET_ARN = os.environ['SECRET_ARN']
DATABASE = os.environ['DATABASE_NAME']

def handler(event, context):
    \"\"\"
    Knowledge search tool for AgentCore Gateway.
    Searches articles by keyword, scoped to the tenant via RLS.
    \"\"\"
    tenant_id = event.get('tenant_id', '')
    query = event.get('query', '')
    category = event.get('category', None)

    # Set tenant context for RLS
    rds_client.execute_statement(
        resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN,
        database=DATABASE,
        sql=f"SET app.current_tenant_id = '{tenant_id}'"
    )

    sql = \"\"\"
        SELECT article_id, title, content, category, tags
        FROM knowledge_articles
        WHERE (title ILIKE :query OR content ILIKE :query)
    \"\"\"
    params = [{'name': 'query', 'value': {'stringValue': f'%{query}%'}}]

    if category:
        sql += " AND category = :cat"
        params.append({'name': 'cat', 'value': {'stringValue': category}})

    sql += " ORDER BY created_at DESC LIMIT 10"

    result = rds_client.execute_statement(
        resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN,
        database=DATABASE, sql=sql, parameters=params,
    )

    return {
        'statusCode': 200,
        'body': json.dumps({
            'articles': str(result.get('records', [])),
            'count': len(result.get('records', [])),
        })
    }
"""
            ),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=tool_env,
        )
        self.knowledge_search_lambda.add_to_role_policy(rds_data_policy)
        self.knowledge_search_lambda.add_to_role_policy(secrets_policy)

        # -----------------------------------------------------------
        # Tool Lambda: Billing Inquiry
        # Retrieves billing records for the tenant.
        # -----------------------------------------------------------
        self.billing_inquiry_lambda = lambda_.Function(
            self,
            "BillingInquiryLambda",
            function_name="agentcore-tool-billing-inquiry",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                """
import json
import boto3
import os

rds_client = boto3.client('rds-data')
CLUSTER_ARN = os.environ['CLUSTER_ARN']
SECRET_ARN = os.environ['SECRET_ARN']
DATABASE = os.environ['DATABASE_NAME']

def handler(event, context):
    \"\"\"
    Billing inquiry tool for AgentCore Gateway.
    Retrieves billing records scoped to the tenant via RLS.
    \"\"\"
    tenant_id = event.get('tenant_id', '')
    action = event.get('action', 'list_invoices')

    # Set tenant context for RLS
    rds_client.execute_statement(
        resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN,
        database=DATABASE,
        sql=f"SET app.current_tenant_id = '{tenant_id}'"
    )

    if action == 'list_invoices':
        result = rds_client.execute_statement(
            resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN,
            database=DATABASE,
            sql="SELECT * FROM billing_records ORDER BY created_at DESC LIMIT 20",
        )
        return {'statusCode': 200, 'body': json.dumps({'invoices': str(result.get('records', []))})}

    elif action == 'get_balance':
        result = rds_client.execute_statement(
            resourceArn=CLUSTER_ARN, secretArn=SECRET_ARN,
            database=DATABASE,
            sql="SELECT SUM(amount) as total FROM billing_records WHERE status = 'pending'",
        )
        return {'statusCode': 200, 'body': json.dumps({'balance': str(result.get('records', []))})}

    return {'statusCode': 400, 'body': json.dumps({'error': f'Unknown action: {action}'})}
"""
            ),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment=tool_env,
        )
        self.billing_inquiry_lambda.add_to_role_policy(rds_data_policy)
        self.billing_inquiry_lambda.add_to_role_policy(secrets_policy)

        # -----------------------------------------------------------
        # Interceptor Lambda
        # Runs before every agent invocation to extract tenant context
        # from the JWT token and inject it into the request.
        # -----------------------------------------------------------
        self.interceptor_lambda = lambda_.Function(
            self,
            "InterceptorLambda",
            function_name="agentcore-gateway-interceptor",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                """
import json
import base64

def handler(event, context):
    \"\"\"
    AgentCore Gateway Interceptor.
    Extracts tenant_id from the JWT token in the authorization header
    and injects it into the request context so that downstream tools
    can enforce tenant isolation.
    \"\"\"
    print(f"Interceptor invoked: {json.dumps(event)}")

    # Extract authorization token
    headers = event.get('headers', {})
    auth_header = headers.get('Authorization', headers.get('authorization', ''))

    tenant_id = 'unknown'
    user_id = 'unknown'

    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        try:
            # Decode JWT payload (middle segment) without verification
            # (Cognito already verified the token)
            payload = token.split('.')[1]
            # Add padding
            payload += '=' * (4 - len(payload) % 4)
            decoded = json.loads(base64.b64decode(payload))
            tenant_id = decoded.get('custom:tenantId', 'unknown')
            user_id = decoded.get('sub', decoded.get('username', 'unknown'))
        except Exception as e:
            print(f"Token decode error: {e}")

    print(f"Interceptor: tenant_id={tenant_id}, user_id={user_id}")

    # Return enriched context for downstream tools
    return {
        'statusCode': 200,
        'context': {
            'tenant_id': tenant_id,
            'user_id': user_id,
        },
        'headers': event.get('headers', {}),
        'body': event.get('body', ''),
    }
"""
            ),
            timeout=Duration.seconds(10),
            memory_size=128,
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        # -----------------------------------------------------------
        # AgentCore Gateway Custom Resource
        # Creates the Gateway via the Bedrock AgentCore API since
        # no L2 CDK construct exists yet.
        # -----------------------------------------------------------
        gateway_cr_lambda = lambda_.Function(
            self,
            "GatewayCustomResourceLambda",
            function_name="agentcore-gateway-cr",
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
    Custom Resource to create/update/delete an AgentCore Gateway.
    Uses the bedrock-agentcore API (boto3).
    \"\"\"
    props = event['ResourceProperties']
    request_type = event['RequestType']

    try:
        client = boto3.client('bedrock-agentcore')

        if request_type == 'Create':
            response = client.create_gateway(
                name=props['GatewayName'],
                description=props.get('Description', ''),
                roleArn=props['RoleArn'],
                protocolConfiguration={
                    'mcp': {
                        'supportedVersions': ['2025-06-18'],
                        'instructions': props.get('Instructions', ''),
                    }
                },
                authorizationConfiguration={
                    'authorizationType': 'CUSTOM_JWT',
                    'customJWTAuthorizationConfiguration': {
                        'discoveryUrl': props['DiscoveryUrl'],
                        'allowedAudiences': [props['AllowedAudience']],
                        'allowedClients': [props['AllowedClient']],
                    }
                },
            )
            gateway_id = response['gatewayId']
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                'GatewayId': gateway_id,
            }, gateway_id)

        elif request_type == 'Update':
            gateway_id = event['PhysicalResourceId']
            client.update_gateway(
                gatewayId=gateway_id,
                name=props['GatewayName'],
                description=props.get('Description', ''),
            )
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                'GatewayId': gateway_id,
            }, gateway_id)

        elif request_type == 'Delete':
            gateway_id = event['PhysicalResourceId']
            try:
                # Delete all targets first
                targets = client.list_gateway_targets(gatewayId=gateway_id)
                for target in targets.get('items', []):
                    client.delete_gateway_target(
                        gatewayId=gateway_id,
                        targetId=target['targetId'],
                    )
                client.delete_gateway(gatewayId=gateway_id)
            except client.exceptions.ResourceNotFoundException:
                pass
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, gateway_id)

    except Exception as e:
        print(f"Error: {str(e)}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': str(e)})
"""
            ),
            timeout=Duration.minutes(5),
            memory_size=256,
        )

        # Grant broad bedrock-agentcore permissions to the CR Lambda
        gateway_cr_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:*",
                    "iam:PassRole",
                ],
                resources=["*"],
            )
        )

        # Create the Gateway via Custom Resource
        self.gateway_resource = CustomResource(
            self,
            "AgentCoreGateway",
            service_token=gateway_cr_lambda.function_arn,
            properties={
                "GatewayName": "agentcore-multi-tenant-gateway",
                "Description": "Multi-tenant SaaS customer support gateway",
                "RoleArn": service_role_arn,
                "DiscoveryUrl": f"https://cognito-idp.{self.region}.amazonaws.com/{self.node.try_get_context('user_pool_id') or 'PLACEHOLDER'}/.well-known/openid-configuration",
                "AllowedAudience": self.node.try_get_context("user_pool_client_id") or "PLACEHOLDER",
                "AllowedClient": self.node.try_get_context("user_pool_client_id") or "PLACEHOLDER",
                "Instructions": "You are a multi-tenant customer support agent. Always use the tenant_id from the request context to scope all operations.",
            },
        )

        self.gateway_id = self.gateway_resource.get_att_string("GatewayId")

        # -----------------------------------------------------------
        # Gateway Target Custom Resource Lambda
        # Registers tool Lambda functions as Gateway targets.
        # -----------------------------------------------------------
        target_cr_lambda = lambda_.Function(
            self,
            "TargetCustomResourceLambda",
            function_name="agentcore-gateway-target-cr",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.Code.from_inline(
                """
import json
import boto3
import cfnresponse

def handler(event, context):
    \"\"\"
    Custom Resource to create/delete Gateway Targets (tool Lambda functions).
    \"\"\"
    props = event['ResourceProperties']
    request_type = event['RequestType']

    try:
        client = boto3.client('bedrock-agentcore')

        if request_type in ('Create', 'Update'):
            response = client.create_gateway_target(
                gatewayId=props['GatewayId'],
                name=props['TargetName'],
                description=props.get('Description', ''),
                targetConfiguration={
                    'mcp': {
                        'lambdaTargetConfiguration': {
                            'lambdaArn': props['LambdaArn'],
                        },
                    },
                },
            )
            target_id = response['targetId']
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {
                'TargetId': target_id,
            }, target_id)

        elif request_type == 'Delete':
            target_id = event['PhysicalResourceId']
            try:
                client.delete_gateway_target(
                    gatewayId=props['GatewayId'],
                    targetId=target_id,
                )
            except Exception:
                pass
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, target_id)

    except Exception as e:
        print(f"Error: {str(e)}")
        cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': str(e)})
"""
            ),
            timeout=Duration.minutes(5),
            memory_size=256,
        )

        target_cr_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:*", "iam:PassRole"],
                resources=["*"],
            )
        )

        # Register tool targets
        ticket_target = CustomResource(
            self,
            "TicketManagementTarget",
            service_token=target_cr_lambda.function_arn,
            properties={
                "GatewayId": self.gateway_id,
                "TargetName": "ticket-management",
                "Description": "Manage support tickets: list, create, update, get ticket details",
                "LambdaArn": self.ticket_management_lambda.function_arn,
            },
        )
        ticket_target.node.add_dependency(self.gateway_resource)

        knowledge_target = CustomResource(
            self,
            "KnowledgeSearchTarget",
            service_token=target_cr_lambda.function_arn,
            properties={
                "GatewayId": self.gateway_id,
                "TargetName": "knowledge-search",
                "Description": "Search knowledge base articles by keyword and category",
                "LambdaArn": self.knowledge_search_lambda.function_arn,
            },
        )
        knowledge_target.node.add_dependency(self.gateway_resource)

        billing_target = CustomResource(
            self,
            "BillingInquiryTarget",
            service_token=target_cr_lambda.function_arn,
            properties={
                "GatewayId": self.gateway_id,
                "TargetName": "billing-inquiry",
                "Description": "Query billing records and account balance",
                "LambdaArn": self.billing_inquiry_lambda.function_arn,
            },
        )
        billing_target.node.add_dependency(self.gateway_resource)

        # -----------------------------------------------------------
        # Outputs
        # -----------------------------------------------------------
        CfnOutput(
            self,
            "GatewayId",
            value=self.gateway_id,
            description="AgentCore Gateway ID",
            export_name="AgentCoreGatewayId",
        )

        CfnOutput(
            self,
            "TicketManagementLambdaArn",
            value=self.ticket_management_lambda.function_arn,
            description="Ticket management tool Lambda ARN",
        )

        CfnOutput(
            self,
            "KnowledgeSearchLambdaArn",
            value=self.knowledge_search_lambda.function_arn,
            description="Knowledge search tool Lambda ARN",
        )

        CfnOutput(
            self,
            "BillingInquiryLambdaArn",
            value=self.billing_inquiry_lambda.function_arn,
            description="Billing inquiry tool Lambda ARN",
        )

        CfnOutput(
            self,
            "InterceptorLambdaArn",
            value=self.interceptor_lambda.function_arn,
            description="Gateway interceptor Lambda ARN",
        )
