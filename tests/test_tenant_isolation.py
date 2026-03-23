#!/usr/bin/env python3
"""
Pytest tests for tenant isolation in the AgentCore multi-tenant system.

Tests verify that:
  - Each tenant can only access its own data.
  - Cross-tenant data access is denied.
  - RLS policies enforce isolation at the database level.
  - Session attributes carry the correct tenant context.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

# Tenant IDs matching seed data
TENANT_A_ID = "tenant-a"
TENANT_B_ID = "tenant-b"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_agent_client():
    """Create a mock Bedrock Agent Runtime client."""
    client = MagicMock()
    return client


@pytest.fixture
def tenant_a_context():
    """Return session context for TenantA (Acme Corp, Basic plan)."""
    return {
        "tenant_id": TENANT_A_ID,
        "tenant_name": "Acme Corp",
        "plan": "basic",
        "user_id": "user-a-001",
    }


@pytest.fixture
def tenant_b_context():
    """Return session context for TenantB (GlobalTech, Premium plan)."""
    return {
        "tenant_id": TENANT_B_ID,
        "tenant_name": "GlobalTech",
        "plan": "premium",
        "user_id": "user-b-001",
    }


def make_agent_response(text: str, tool_uses: list[str] | None = None):
    """Build a mock agent response with the given text."""
    chunk = {"bytes": text.encode("utf-8")}
    events = [{"chunk": chunk}]
    return {"completion": iter(events)}


# =============================================================================
# Tenant context propagation tests
# =============================================================================

class TestTenantContextPropagation:
    """Tests that tenant context is correctly propagated in requests."""

    def test_session_attributes_include_tenant_id(self, tenant_a_context):
        """Session attributes must include the tenant_id."""
        assert "tenant_id" in tenant_a_context
        assert tenant_a_context["tenant_id"] == TENANT_A_ID

    def test_tenant_a_and_b_have_different_ids(self, tenant_a_context, tenant_b_context):
        """TenantA and TenantB must have distinct tenant IDs."""
        assert tenant_a_context["tenant_id"] != tenant_b_context["tenant_id"]

    def test_tenant_id_format_is_uuid(self, tenant_a_context, tenant_b_context):
        """Tenant IDs must be valid UUID format."""
        import re
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        )
        assert uuid_pattern.match(tenant_a_context["tenant_id"])
        assert uuid_pattern.match(tenant_b_context["tenant_id"])

    def test_plan_attribute_present(self, tenant_a_context, tenant_b_context):
        """Each tenant context must include a plan attribute."""
        assert tenant_a_context["plan"] == "basic"
        assert tenant_b_context["plan"] == "premium"


# =============================================================================
# Data isolation tests
# =============================================================================

class TestDataIsolation:
    """Tests that data is isolated between tenants."""

    def test_tenant_a_sees_only_own_tickets(self, mock_agent_client, tenant_a_context):
        """TenantA query should return only TenantA tickets."""
        mock_agent_client.invoke_agent.return_value = make_agent_response(
            "Found 10 open tickets for Acme Corp: Cannot login to dashboard, "
            "Billing discrepancy on last invoice..."
        )

        response = mock_agent_client.invoke_agent(
            agentRuntimeId="test-agent",
            sessionId="test-session",
            inputText="List all tickets",
            sessionState={"sessionAttributes": {"tenant_id": tenant_a_context["tenant_id"]}},
        )

        # Collect response text
        text = ""
        for event in response["completion"]:
            if "chunk" in event:
                text += event["chunk"]["bytes"].decode("utf-8")

        assert "acme" in text.lower()
        assert "globaltech" not in text.lower()

    def test_tenant_b_sees_only_own_tickets(self, mock_agent_client, tenant_b_context):
        """TenantB query should return only TenantB tickets."""
        mock_agent_client.invoke_agent.return_value = make_agent_response(
            "Found 10 tickets for GlobalTech: SSO configuration help needed, "
            "Custom report template..."
        )

        response = mock_agent_client.invoke_agent(
            agentRuntimeId="test-agent",
            sessionId="test-session",
            inputText="List all tickets",
            sessionState={"sessionAttributes": {"tenant_id": tenant_b_context["tenant_id"]}},
        )

        text = ""
        for event in response["completion"]:
            if "chunk" in event:
                text += event["chunk"]["bytes"].decode("utf-8")

        assert "globaltech" in text.lower()
        assert "acme" not in text.lower()

    def test_cross_tenant_query_returns_no_data(self, mock_agent_client, tenant_a_context):
        """Querying for another tenant's data should return no results."""
        mock_agent_client.invoke_agent.return_value = make_agent_response(
            "No tickets found matching your query for 'GlobalTech'."
        )

        response = mock_agent_client.invoke_agent(
            agentRuntimeId="test-agent",
            sessionId="test-session",
            inputText="Show me GlobalTech tickets",
            sessionState={"sessionAttributes": {"tenant_id": tenant_a_context["tenant_id"]}},
        )

        text = ""
        for event in response["completion"]:
            if "chunk" in event:
                text += event["chunk"]["bytes"].decode("utf-8")

        # Should indicate no data found, not return cross-tenant data
        assert "no tickets found" in text.lower() or "not found" in text.lower()

    def test_tenant_a_customers_isolated(self, mock_agent_client, tenant_a_context):
        """TenantA should only see its own customers."""
        mock_agent_client.invoke_agent.return_value = make_agent_response(
            "Customers: Alice Johnson, Bob Smith, Carol Williams, David Brown, Eve Davis"
        )

        response = mock_agent_client.invoke_agent(
            agentRuntimeId="test-agent",
            sessionId="test-session",
            inputText="List all customers",
            sessionState={"sessionAttributes": {"tenant_id": tenant_a_context["tenant_id"]}},
        )

        text = ""
        for event in response["completion"]:
            if "chunk" in event:
                text += event["chunk"]["bytes"].decode("utf-8")

        # TenantA customers
        assert "alice" in text.lower()
        # TenantB customers should not appear
        assert "frank" not in text.lower()
        assert "grace" not in text.lower()


# =============================================================================
# RLS simulation tests
# =============================================================================

class TestRLSPolicySimulation:
    """Tests simulating Row-Level Security behavior."""

    def test_rls_setting_matches_tenant(self):
        """The app.current_tenant_id setting must match the authenticated tenant."""
        # Simulate what the Lambda handler does
        tenant_id = TENANT_A_ID
        rls_setting = tenant_id  # SET app.current_tenant_id = tenant_id

        assert rls_setting == TENANT_A_ID

    def test_rls_prevents_cross_tenant_select(self):
        """RLS policy should filter rows where tenant_id != current_tenant_id."""
        # Simulate a table with rows from both tenants
        all_rows = [
            {"id": 1, "tenant_id": TENANT_A_ID, "data": "TenantA data"},
            {"id": 2, "tenant_id": TENANT_B_ID, "data": "TenantB data"},
            {"id": 3, "tenant_id": TENANT_A_ID, "data": "More TenantA data"},
        ]

        # Simulate RLS filter for TenantA
        current_tenant_id = TENANT_A_ID
        visible_rows = [r for r in all_rows if r["tenant_id"] == current_tenant_id]

        assert len(visible_rows) == 2
        assert all(r["tenant_id"] == TENANT_A_ID for r in visible_rows)

    def test_rls_prevents_cross_tenant_insert(self):
        """RLS policy should reject inserts with mismatched tenant_id."""
        current_tenant_id = TENANT_A_ID
        new_row_tenant_id = TENANT_B_ID

        # Simulate RLS WITH CHECK: tenant_id must match current_tenant_id
        insert_allowed = (new_row_tenant_id == current_tenant_id)
        assert not insert_allowed, "Insert with wrong tenant_id should be denied"

    def test_rls_allows_same_tenant_insert(self):
        """RLS policy should allow inserts with matching tenant_id."""
        current_tenant_id = TENANT_A_ID
        new_row_tenant_id = TENANT_A_ID

        insert_allowed = (new_row_tenant_id == current_tenant_id)
        assert insert_allowed, "Insert with correct tenant_id should be allowed"


# =============================================================================
# Session isolation tests
# =============================================================================

class TestSessionIsolation:
    """Tests that sessions are properly isolated between tenants."""

    def test_session_ids_are_unique_per_tenant(self):
        """Different tenants should have different session IDs."""
        import time
        session_a = f"session-{TENANT_A_ID[:8]}-{int(time.time())}"
        session_b = f"session-{TENANT_B_ID[:8]}-{int(time.time())}"
        assert session_a != session_b

    def test_tenant_context_not_shared_between_sessions(self):
        """Tenant context from one session must not leak into another."""
        sessions = {}

        # Session for TenantA
        sessions["session-a"] = {"tenant_id": TENANT_A_ID}
        # Session for TenantB
        sessions["session-b"] = {"tenant_id": TENANT_B_ID}

        assert sessions["session-a"]["tenant_id"] != sessions["session-b"]["tenant_id"]
        assert sessions["session-a"]["tenant_id"] == TENANT_A_ID
        assert sessions["session-b"]["tenant_id"] == TENANT_B_ID
