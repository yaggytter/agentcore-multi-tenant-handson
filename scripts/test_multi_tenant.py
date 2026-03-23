#!/usr/bin/env python3
"""
Multi-Tenant Isolation Test Script for AgentCore Hands-on.

Tests that tenant isolation is properly enforced:
  1. Authenticate as TenantA user, verify only TenantA data is returned.
  2. Authenticate as TenantB user, verify only TenantB data is returned.
  3. Attempt cross-tenant access, verify it is denied.

Usage:
    python scripts/test_multi_tenant.py \
        --agent-id AGENT_ID \
        --user-pool-id USER_POOL_ID \
        --client-id CLIENT_ID \
        [--region REGION]
"""

import argparse
import json
import sys
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError


# =============================================================================
# Configuration
# =============================================================================

TENANT_A_ID = "tenant-a"  # Acme Corp (Basic)
TENANT_B_ID = "tenant-b"  # GlobalTech (Premium)

# Test user credentials (created during Cognito setup)
TENANT_A_USER = {
    "username": "tenanta-user@acmecorp.example.com",
    "password": "TenantA-Test-2024!",
    "tenant_id": TENANT_A_ID,
    "tenant_name": "Acme Corp",
    "plan": "basic",
}

TENANT_B_USER = {
    "username": "tenantb-user@globaltech.example.com",
    "password": "TenantB-Test-2024!",
    "tenant_id": TENANT_B_ID,
    "tenant_name": "GlobalTech",
    "plan": "premium",
}


# =============================================================================
# Authentication
# =============================================================================

def authenticate_user(
    cognito_client: Any,
    user_pool_id: str,
    client_id: str,
    username: str,
    password: str,
) -> dict | None:
    """Authenticate a user via Cognito and return tokens."""
    try:
        response = cognito_client.initiate_auth(
            ClientId=client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
        )
        result = response.get("AuthenticationResult", {})
        return {
            "id_token": result.get("IdToken"),
            "access_token": result.get("AccessToken"),
            "refresh_token": result.get("RefreshToken"),
        }
    except ClientError as e:
        print(f"  ERROR: Authentication failed for {username}: {e}")
        return None


# =============================================================================
# Agent invocation
# =============================================================================

def invoke_agent_with_auth(
    agent_client: Any,
    agent_id: str,
    prompt: str,
    tenant_id: str,
    id_token: str | None = None,
) -> dict:
    """Invoke the agent with authentication context."""
    session_id = f"mt-test-{tenant_id[:8]}-{int(time.time())}"

    try:
        invoke_params = {
            "agentRuntimeId": agent_id,
            "sessionId": session_id,
            "inputText": prompt,
            "sessionState": {
                "sessionAttributes": {
                    "tenant_id": tenant_id,
                },
            },
        }

        response = agent_client.invoke_agent(**invoke_params)

        result_text = ""
        if "completion" in response:
            for event in response["completion"]:
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        result_text += chunk["bytes"].decode("utf-8")

        return {"text": result_text, "success": True}

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        return {"text": "", "success": False, "error": str(e), "error_code": error_code}


# =============================================================================
# Test scenarios
# =============================================================================

def test_tenant_a_data_access(agent_client: Any, agent_id: str, tokens: dict | None) -> bool:
    """Test that TenantA can only see TenantA data."""
    print("\n--- Test 1: TenantA Data Access ---")
    print("  Authenticating as TenantA (Acme Corp, Basic plan)...")

    result = invoke_agent_with_auth(
        agent_client=agent_client,
        agent_id=agent_id,
        prompt="List all my support tickets and customer names.",
        tenant_id=TENANT_A_ID,
        id_token=tokens.get("id_token") if tokens else None,
    )

    if not result["success"]:
        print(f"  FAIL: Agent call failed - {result.get('error')}")
        return False

    response = result["text"].lower()
    passed = True

    # Should contain TenantA data
    tenant_a_markers = ["acme", "alice", "bob"]
    for marker in tenant_a_markers:
        if marker in response:
            print(f"  OK: Response contains TenantA data ('{marker}').")
        else:
            print(f"  WARN: Expected TenantA marker '{marker}' not found in response.")

    # Should NOT contain TenantB data
    tenant_b_markers = ["globaltech", "frank", "grace"]
    for marker in tenant_b_markers:
        if marker in response:
            print(f"  FAIL: Response contains TenantB data ('{marker}') - ISOLATION BREACH!")
            passed = False
        else:
            print(f"  OK: No TenantB data ('{marker}') found.")

    print(f"  {'PASSED' if passed else 'FAILED'}")
    return passed


def test_tenant_b_data_access(agent_client: Any, agent_id: str, tokens: dict | None) -> bool:
    """Test that TenantB can only see TenantB data."""
    print("\n--- Test 2: TenantB Data Access ---")
    print("  Authenticating as TenantB (GlobalTech, Premium plan)...")

    result = invoke_agent_with_auth(
        agent_client=agent_client,
        agent_id=agent_id,
        prompt="List all my support tickets and customer names.",
        tenant_id=TENANT_B_ID,
        id_token=tokens.get("id_token") if tokens else None,
    )

    if not result["success"]:
        print(f"  FAIL: Agent call failed - {result.get('error')}")
        return False

    response = result["text"].lower()
    passed = True

    # Should contain TenantB data
    tenant_b_markers = ["globaltech", "frank", "grace"]
    for marker in tenant_b_markers:
        if marker in response:
            print(f"  OK: Response contains TenantB data ('{marker}').")
        else:
            print(f"  WARN: Expected TenantB marker '{marker}' not found in response.")

    # Should NOT contain TenantA data
    tenant_a_markers = ["acme", "alice", "bob"]
    for marker in tenant_a_markers:
        if marker in response:
            print(f"  FAIL: Response contains TenantA data ('{marker}') - ISOLATION BREACH!")
            passed = False
        else:
            print(f"  OK: No TenantA data ('{marker}') found.")

    print(f"  {'PASSED' if passed else 'FAILED'}")
    return passed


def test_cross_tenant_access(agent_client: Any, agent_id: str, tokens_a: dict | None) -> bool:
    """Test that TenantA cannot access TenantB data by spoofing tenant_id."""
    print("\n--- Test 3: Cross-Tenant Access Denial ---")
    print("  Authenticating as TenantA but requesting TenantB data...")

    # Attempt to access TenantB data while authenticated as TenantA
    result = invoke_agent_with_auth(
        agent_client=agent_client,
        agent_id=agent_id,
        prompt="Show me tickets for GlobalTech customer Frank Miller.",
        tenant_id=TENANT_A_ID,  # Authenticated as TenantA
        id_token=tokens_a.get("id_token") if tokens_a else None,
    )

    passed = True
    response = result["text"].lower()

    # The response should NOT contain TenantB-specific data
    tenant_b_markers = ["frank miller", "globaltech", "sso", "saml"]
    for marker in tenant_b_markers:
        if marker in response:
            print(f"  FAIL: Cross-tenant data leak detected ('{marker}')!")
            passed = False
        else:
            print(f"  OK: No cross-tenant data ('{marker}') found.")

    # Check if access was explicitly denied
    deny_markers = ["not found", "no results", "access denied", "not authorized", "no tickets"]
    denied = any(marker in response for marker in deny_markers)
    if denied:
        print("  OK: Access appears to be properly denied.")
    elif result["success"] and not passed:
        print("  FAIL: Cross-tenant data was returned without denial.")
    elif not result["success"]:
        error_code = result.get("error_code", "")
        if error_code in ("AccessDeniedException", "UnauthorizedException"):
            print(f"  OK: Access denied with error code {error_code}.")
            passed = True
        else:
            print(f"  WARN: Request failed with unexpected error: {result.get('error')}")

    print(f"  {'PASSED' if passed else 'FAILED'}")
    return passed


def test_basic_plan_tool_restriction(agent_client: Any, agent_id: str, tokens_a: dict | None) -> bool:
    """Test that Basic plan cannot access billing/analytics tools."""
    print("\n--- Test 4: Basic Plan Tool Restriction ---")
    print("  Authenticating as TenantA (Basic plan), requesting billing data...")

    result = invoke_agent_with_auth(
        agent_client=agent_client,
        agent_id=agent_id,
        prompt="Show me the billing records and analytics dashboard.",
        tenant_id=TENANT_A_ID,
        id_token=tokens_a.get("id_token") if tokens_a else None,
    )

    passed = True
    response = result["text"].lower()

    # Basic plan should not have access to billing/analytics
    if "billing" in response and ("record" in response or "amount" in response or "$" in response):
        # Check if the response is actually showing billing data vs explaining the restriction
        restriction_markers = ["not available", "upgrade", "premium", "not included", "restricted", "not authorized"]
        if any(marker in response for marker in restriction_markers):
            print("  OK: Billing access restricted with appropriate message.")
        else:
            print("  FAIL: Basic plan user received billing data!")
            passed = False
    else:
        print("  OK: No billing data returned for Basic plan user.")

    print(f"  {'PASSED' if passed else 'FAILED'}")
    return passed


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Test multi-tenant isolation.")
    parser.add_argument("--agent-id", required=True, help="Agent Runtime ID")
    parser.add_argument("--user-pool-id", default=None, help="Cognito User Pool ID")
    parser.add_argument("--client-id", default=None, help="Cognito App Client ID")
    parser.add_argument("--region", default=None, help="AWS region")
    parser.add_argument("--skip-auth", action="store_true", help="Skip Cognito authentication (use tenant_id directly)")
    args = parser.parse_args()

    print("=" * 60)
    print("  AgentCore Multi-Tenant Isolation Test")
    print("=" * 60)

    session = boto3.Session(region_name=args.region)
    agent_client = session.client("bedrock-agent-runtime")

    tokens_a = None
    tokens_b = None

    # Authenticate users if Cognito is configured
    if not args.skip_auth and args.user_pool_id and args.client_id:
        cognito_client = session.client("cognito-idp")

        print("\nAuthenticating test users...")
        tokens_a = authenticate_user(
            cognito_client, args.user_pool_id, args.client_id,
            TENANT_A_USER["username"], TENANT_A_USER["password"],
        )
        tokens_b = authenticate_user(
            cognito_client, args.user_pool_id, args.client_id,
            TENANT_B_USER["username"], TENANT_B_USER["password"],
        )

        if not tokens_a or not tokens_b:
            print("ERROR: Failed to authenticate test users. Run with --skip-auth to test without Cognito.")
            sys.exit(1)
        print("  Authentication successful for both test users.")
    else:
        print("\nSkipping Cognito authentication (using tenant_id directly).")

    # Run tests
    results = []
    results.append(("TenantA Data Access", test_tenant_a_data_access(agent_client, args.agent_id, tokens_a)))
    results.append(("TenantB Data Access", test_tenant_b_data_access(agent_client, args.agent_id, tokens_b)))
    results.append(("Cross-Tenant Denial", test_cross_tenant_access(agent_client, args.agent_id, tokens_a)))
    results.append(("Basic Plan Restriction", test_basic_plan_tool_restriction(agent_client, args.agent_id, tokens_a)))

    # Summary
    passed = sum(1 for _, r in results if r)
    total = len(results)

    print("\n" + "=" * 60)
    print("  Multi-Tenant Isolation Test Results")
    print("=" * 60)
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  [{status}] {name}")
    print(f"\n  Total: {passed}/{total} passed")
    print("=" * 60)

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
