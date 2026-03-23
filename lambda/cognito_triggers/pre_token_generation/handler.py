"""
Cognito Pre-Token Generation Trigger Lambda
Adds custom tenant claims to JWT tokens issued by Cognito.
"""

import json
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB table that maps users to tenants
TENANT_TABLE_NAME = os.environ.get("TENANT_TABLE_NAME", "TenantMappings")

dynamodb = boto3.resource("dynamodb")


def get_tenant_info(user_sub: str, username: str) -> dict:
    """
    Look up tenant information for a user from DynamoDB.
    Falls back to user attributes if DynamoDB lookup fails.
    """
    try:
        table = dynamodb.Table(TENANT_TABLE_NAME)
        response = table.get_item(
            Key={"userId": user_sub},
        )
        item = response.get("Item")
        if item:
            return {
                "tenantId": item.get("tenantId", ""),
                "tenantName": item.get("tenantName", ""),
                "tenantPlan": item.get("tenantPlan", ""),
                "role": item.get("role", "user"),
            }
    except ClientError as e:
        logger.warning(
            f"DynamoDB lookup failed for user {user_sub}: {e}"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error looking up tenant for user {user_sub}: {e}"
        )

    return {}


def lambda_handler(event, context):
    """
    Cognito Pre-Token Generation trigger handler.

    This trigger fires before Cognito issues a token (ID or Access token).
    It adds custom claims with tenant information so that downstream
    services (AgentCore Gateway, interceptors) can identify the tenant.

    Event structure:
    {
        "version": "1",
        "triggerSource": "TokenGeneration_HostedAuth" | "TokenGeneration_Authentication",
        "region": "us-east-1",
        "userPoolId": "us-east-1_xxxxx",
        "userName": "user@example.com",
        "callerContext": { ... },
        "request": {
            "userAttributes": {
                "sub": "uuid",
                "email": "user@example.com",
                "custom:tenantId": "tenant-a",
                ...
            },
            "groupConfiguration": { ... }
        },
        "response": {
            "claimsOverrideDetails": null
        }
    }
    """
    logger.info(f"Pre-token generation trigger: {json.dumps(event)}")

    try:
        user_attributes = event["request"].get("userAttributes", {})
        user_sub = user_attributes.get("sub", "")
        username = event.get("userName", "")

        # First check if tenant info is already in user attributes
        tenant_id = user_attributes.get("custom:tenantId", "")
        tenant_name = user_attributes.get("custom:tenantName", "")
        tenant_plan = user_attributes.get("custom:tenantPlan", "")

        # If not in user attributes, look up from DynamoDB
        if not tenant_id:
            tenant_info = get_tenant_info(user_sub, username)
            tenant_id = tenant_info.get("tenantId", "")
            tenant_name = tenant_info.get("tenantName", "")
            tenant_plan = tenant_info.get("tenantPlan", "")

        if not tenant_id:
            logger.error(
                f"No tenant mapping found for user {username} ({user_sub})"
            )
            # Allow token generation but without tenant claims.
            # The interceptor will reject requests without tenant_id.
            event["response"]["claimsOverrideDetails"] = {
                "claimsToAddOrOverride": {
                    "custom:tenantId": "",
                    "custom:tenantName": "",
                    "custom:tenantPlan": "",
                },
            }
            return event

        logger.info(
            f"Adding tenant claims for user {username}: "
            f"tenantId={tenant_id}, tenantName={tenant_name}, plan={tenant_plan}"
        )

        # Add custom claims to the token
        event["response"]["claimsOverrideDetails"] = {
            "claimsToAddOrOverride": {
                "custom:tenantId": tenant_id,
                "custom:tenantName": tenant_name,
                "custom:tenantPlan": tenant_plan,
            },
            # Optionally suppress default claims to reduce token size
            "claimsToSuppress": [],
        }

        # Add group-based claims if user belongs to tenant admin group
        group_config = event["request"].get("groupConfiguration", {})
        groups = group_config.get("groupsToOverride", [])
        if groups:
            logger.info(f"User {username} belongs to groups: {groups}")

        return event

    except KeyError as e:
        logger.error(f"Missing expected field in event: {e}")
        # Return event unchanged to avoid blocking authentication
        return event
    except Exception as e:
        logger.error(f"Pre-token generation failed: {e}", exc_info=True)
        # Return event unchanged to avoid blocking authentication
        return event
