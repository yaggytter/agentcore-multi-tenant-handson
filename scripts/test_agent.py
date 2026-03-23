#!/usr/bin/env python3
"""
Agent Test Script for AgentCore Multi-Tenant Hands-on.

Invokes the customer support agent with various test prompts, verifies
responses, and validates tool usage.

Usage:
    python scripts/test_agent.py [--agent-id AGENT_ID] [--region REGION]
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

# Test tenant IDs (must match seed data)
TENANT_A_ID = "tenant-a"  # Acme Corp (Basic)
TENANT_B_ID = "tenant-b"  # GlobalTech (Premium)

# Test prompts with expected behaviors
TEST_CASES = [
    {
        "name": "Search tickets - TenantA",
        "tenant_id": TENANT_A_ID,
        "prompt": "Show me all open support tickets.",
        "expect_tool": "search_tickets",
        "expect_in_response": ["open"],
        "expect_not_in_response": ["GlobalTech"],
    },
    {
        "name": "Search knowledge - TenantA",
        "tenant_id": TENANT_A_ID,
        "prompt": "How do I reset my password?",
        "expect_tool": "search_knowledge",
        "expect_in_response": ["password", "reset"],
    },
    {
        "name": "Create ticket - TenantA",
        "tenant_id": TENANT_A_ID,
        "prompt": "Create a support ticket: subject 'Test Ticket', description 'This is a test ticket for automated testing.', priority 'low'.",
        "expect_tool": "create_ticket",
        "expect_in_response": ["ticket", "created"],
    },
    {
        "name": "Search tickets - TenantB",
        "tenant_id": TENANT_B_ID,
        "prompt": "List all critical tickets.",
        "expect_tool": "search_tickets",
        "expect_in_response": ["critical"],
        "expect_not_in_response": ["Acme"],
    },
    {
        "name": "Billing info - TenantB (Premium)",
        "tenant_id": TENANT_B_ID,
        "prompt": "Show me the billing records for Frank Miller.",
        "expect_tool": "get_billing_info",
        "expect_in_response": ["Frank", "billing"],
    },
    {
        "name": "Analytics - TenantB (Premium)",
        "tenant_id": TENANT_B_ID,
        "prompt": "Show me the ticket analytics for this month.",
        "expect_tool": "get_analytics",
        "expect_in_response": ["analytics"],
    },
]


# =============================================================================
# Helper functions
# =============================================================================

def load_agent_config(project_root: str) -> dict[str, str]:
    """Load agent configuration from CDK outputs."""
    outputs_path = f"{project_root}/cdk-outputs.json"
    try:
        with open(outputs_path) as f:
            outputs = json.load(f)
        # Extract agent ID from outputs (adjust key as needed)
        for stack_name, stack_outputs in outputs.items():
            for key, value in stack_outputs.items():
                if "agentruntime" in key.lower() or "agentid" in key.lower():
                    return {"agent_id": value}
    except FileNotFoundError:
        pass
    return {}


def invoke_agent(
    client: Any,
    agent_id: str,
    prompt: str,
    tenant_id: str,
    session_id: str | None = None,
) -> dict:
    """Invoke the AgentCore Runtime agent and return the response."""
    if session_id is None:
        session_id = f"test-{int(time.time())}"

    try:
        response = client.invoke_agent(
            agentRuntimeId=agent_id,
            sessionId=session_id,
            inputText=prompt,
            sessionState={
                "sessionAttributes": {
                    "tenant_id": tenant_id,
                }
            },
        )

        # Collect response chunks
        result_text = ""
        tool_uses = []

        if "completion" in response:
            for event in response["completion"]:
                if "chunk" in event:
                    chunk = event["chunk"]
                    if "bytes" in chunk:
                        result_text += chunk["bytes"].decode("utf-8")
                if "trace" in event:
                    trace = event["trace"].get("trace", {})
                    orchestration = trace.get("orchestrationTrace", {})
                    if "invocationInput" in orchestration:
                        tool_input = orchestration["invocationInput"]
                        if "toolInvocationInput" in tool_input:
                            tool_name = tool_input["toolInvocationInput"].get("toolName", "")
                            tool_uses.append(tool_name)

        return {
            "text": result_text,
            "tool_uses": tool_uses,
            "session_id": session_id,
            "success": True,
        }

    except ClientError as e:
        return {
            "text": "",
            "tool_uses": [],
            "session_id": session_id,
            "success": False,
            "error": str(e),
        }


def run_test_case(client: Any, agent_id: str, test_case: dict) -> bool:
    """Run a single test case and return True if it passes."""
    name = test_case["name"]
    print(f"\n  Running: {name}")
    print(f"  Prompt: {test_case['prompt'][:80]}...")

    result = invoke_agent(
        client=client,
        agent_id=agent_id,
        prompt=test_case["prompt"],
        tenant_id=test_case["tenant_id"],
    )

    if not result["success"]:
        print(f"  FAIL: Agent invocation failed - {result.get('error', 'Unknown error')}")
        return False

    passed = True
    response_lower = result["text"].lower()

    # Check expected tool usage
    if "expect_tool" in test_case:
        expected_tool = test_case["expect_tool"]
        if expected_tool in result["tool_uses"]:
            print(f"  OK: Tool '{expected_tool}' was used.")
        else:
            print(f"  WARN: Expected tool '{expected_tool}' but got: {result['tool_uses']}")
            # Tool check is a warning, not a hard failure

    # Check expected terms in response
    for term in test_case.get("expect_in_response", []):
        if term.lower() in response_lower:
            print(f"  OK: Response contains '{term}'.")
        else:
            print(f"  FAIL: Response does not contain expected term '{term}'.")
            passed = False

    # Check terms that should NOT be in response
    for term in test_case.get("expect_not_in_response", []):
        if term.lower() not in response_lower:
            print(f"  OK: Response does not contain '{term}' (as expected).")
        else:
            print(f"  FAIL: Response contains unexpected term '{term}' (cross-tenant leak).")
            passed = False

    if passed:
        print(f"  PASSED")
    else:
        print(f"  FAILED")

    return passed


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Test the AgentCore customer support agent.")
    parser.add_argument("--agent-id", help="Agent Runtime ID (auto-detected from cdk-outputs.json if omitted)")
    parser.add_argument("--region", default=None, help="AWS region")
    args = parser.parse_args()

    print("=" * 60)
    print("  AgentCore Multi-Tenant Hands-on - Agent Test")
    print("=" * 60)

    # Determine agent ID
    agent_id = args.agent_id
    if not agent_id:
        config = load_agent_config(".")
        agent_id = config.get("agent_id")

    if not agent_id:
        print("\nERROR: Agent ID not provided and could not be auto-detected.")
        print("Usage: python scripts/test_agent.py --agent-id <AGENT_ID>")
        sys.exit(1)

    print(f"\nAgent ID: {agent_id}")

    # Create Bedrock Agent Runtime client
    session = boto3.Session(region_name=args.region)
    client = session.client("bedrock-agent-runtime")

    # Run test cases
    total = len(TEST_CASES)
    passed = 0
    failed = 0

    for test_case in TEST_CASES:
        if run_test_case(client, agent_id, test_case):
            passed += 1
        else:
            failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"  Results: {passed}/{total} passed, {failed}/{total} failed")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
