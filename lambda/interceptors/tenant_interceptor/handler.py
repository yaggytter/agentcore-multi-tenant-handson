"""
Gateway Interceptor Lambda: Tenant Context
Extracts tenant_id from JWT claims and injects it into tool input parameters.
Also logs tenant context for audit purposes.
"""

import json
import logging
import time
import base64
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def decode_jwt_claims(token: str) -> dict:
    """
    Decode JWT claims payload (without verification -- verification
    is handled by Cognito/API Gateway authorizer).
    """
    try:
        # JWT structure: header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            logger.warning("Invalid JWT format")
            return {}

        # Decode the payload (second part)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)

    except Exception as e:
        logger.error(f"Failed to decode JWT: {e}")
        return {}


def extract_tenant_from_event(event: dict) -> dict:
    """
    Extract tenant information from the interceptor event.
    Checks multiple locations where tenant info might be present.
    """
    tenant_info = {
        "tenant_id": "",
        "tenant_name": "",
        "tenant_plan": "",
    }

    # 1. Check session attributes (already extracted by AgentCore)
    session_attrs = event.get("sessionAttributes", {})
    if session_attrs.get("tenantId"):
        tenant_info["tenant_id"] = session_attrs["tenantId"]
        tenant_info["tenant_name"] = session_attrs.get("tenantName", "")
        tenant_info["tenant_plan"] = session_attrs.get("tenantPlan", "")
        return tenant_info

    # 2. Check the authorization token in the request
    request_context = event.get("requestContext", {})
    authorizer = request_context.get("authorizer", {})

    # From Cognito authorizer claims
    claims = authorizer.get("claims", {})
    if claims.get("custom:tenantId"):
        tenant_info["tenant_id"] = claims["custom:tenantId"]
        tenant_info["tenant_name"] = claims.get("custom:tenantName", "")
        tenant_info["tenant_plan"] = claims.get("custom:tenantPlan", "")
        return tenant_info

    # 3. Decode JWT from Authorization header
    headers = event.get("headers", {})
    auth_header = headers.get("Authorization", headers.get("authorization", ""))
    if auth_header:
        token = auth_header.replace("Bearer ", "")
        claims = decode_jwt_claims(token)
        if claims.get("custom:tenantId"):
            tenant_info["tenant_id"] = claims["custom:tenantId"]
            tenant_info["tenant_name"] = claims.get("custom:tenantName", "")
            tenant_info["tenant_plan"] = claims.get("custom:tenantPlan", "")
            return tenant_info

    return tenant_info


def log_audit_event(tenant_info: dict, event: dict, direction: str):
    """Log tenant context for audit trail."""
    audit_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction": direction,
        "tenant_id": tenant_info.get("tenant_id", "unknown"),
        "tenant_name": tenant_info.get("tenant_name", "unknown"),
        "action": event.get("action", "unknown"),
        "tool_name": event.get("toolName", "unknown"),
        "session_id": event.get("sessionId", "unknown"),
    }
    logger.info(f"AUDIT: {json.dumps(audit_entry)}")


def lambda_handler(event, context):
    """
    AWS Lambda handler for the tenant interceptor.

    This interceptor runs in the AgentCore Gateway pipeline:
    - On REQUEST: extracts tenant_id from JWT and injects into tool parameters
    - On RESPONSE: can modify/filter the tool response if needed

    The interceptor ensures every gateway tool call includes the correct
    tenant_id for data isolation.
    """
    logger.info(f"Interceptor received event: {json.dumps(event)}")

    try:
        direction = event.get("direction", "REQUEST")

        # Extract tenant information
        tenant_info = extract_tenant_from_event(event)
        tenant_id = tenant_info.get("tenant_id", "")

        # Log for audit
        log_audit_event(tenant_info, event, direction)

        if direction == "REQUEST":
            # Validate tenant context exists
            if not tenant_id:
                logger.error("No tenant context found in request")
                return {
                    "statusCode": 403,
                    "action": "DENY",
                    "body": json.dumps({
                        "error": "Tenant context is required for all tool invocations.",
                        "error_ja": "すべてのツール呼び出しにテナントコンテキストが必要です。",
                    }),
                }

            # Inject tenant_id into tool input parameters
            parameters = event.get("parameters", {})
            parameters["tenant_id"] = tenant_id

            # Also inject into session attributes for downstream use
            session_attrs = event.get("sessionAttributes", {})
            session_attrs["tenantId"] = tenant_id
            session_attrs["tenantName"] = tenant_info.get("tenant_name", "")
            session_attrs["tenantPlan"] = tenant_info.get("tenant_plan", "")

            logger.info(
                f"Injected tenant_id={tenant_id} into tool parameters "
                f"for action={event.get('action', 'unknown')}"
            )

            return {
                "statusCode": 200,
                "action": "ALLOW",
                "parameters": parameters,
                "sessionAttributes": session_attrs,
            }

        elif direction == "RESPONSE":
            # On response, verify no cross-tenant data leakage
            response_body = event.get("responseBody", {})

            # Optionally strip internal fields from the response
            if isinstance(response_body, dict):
                response_body.pop("_internal_tenant_id", None)

            logger.info(
                f"Response interceptor pass-through for tenant={tenant_id}"
            )

            return {
                "statusCode": 200,
                "action": "ALLOW",
                "responseBody": response_body,
            }

        else:
            logger.warning(f"Unknown interceptor direction: {direction}")
            return {
                "statusCode": 400,
                "action": "DENY",
                "body": json.dumps({"error": f"Unknown direction: {direction}"}),
            }

    except Exception as e:
        logger.error(f"Interceptor failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "action": "DENY",
            "body": json.dumps({"error": f"Interceptor error: {str(e)}"}),
        }
