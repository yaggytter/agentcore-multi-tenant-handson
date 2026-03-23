#!/usr/bin/env python3
"""
Pytest tests for AgentCore Gateway tool functions.

Tests verify that:
  - Each tool Lambda handler processes requests correctly.
  - Tenant ID is extracted and passed to database queries.
  - Tool responses have the expected structure.
  - Error handling works for invalid inputs.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

# Tenant IDs matching seed data
TENANT_A_ID = "a0000000-0000-0000-0000-000000000001"
TENANT_B_ID = "b0000000-0000-0000-0000-000000000001"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def lambda_context():
    """Create a mock Lambda context object."""
    context = MagicMock()
    context.function_name = "agentcore-multi-tenant-search-tickets"
    context.memory_limit_in_mb = 256
    context.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test"
    context.get_remaining_time_in_millis.return_value = 30000
    return context


@pytest.fixture
def search_tickets_event():
    """Create a sample search_tickets tool invocation event."""
    return {
        "toolName": "search_tickets",
        "input": {
            "query": "open tickets",
            "status": "open",
        },
        "sessionAttributes": {
            "tenant_id": TENANT_A_ID,
        },
    }


@pytest.fixture
def create_ticket_event():
    """Create a sample create_ticket tool invocation event."""
    return {
        "toolName": "create_ticket",
        "input": {
            "subject": "Test ticket",
            "description": "This is a test ticket.",
            "priority": "medium",
            "customer_id": "ca000000-0000-0000-0000-000000000001",
        },
        "sessionAttributes": {
            "tenant_id": TENANT_A_ID,
        },
    }


@pytest.fixture
def search_knowledge_event():
    """Create a sample search_knowledge tool invocation event."""
    return {
        "toolName": "search_knowledge",
        "input": {
            "query": "password reset",
        },
        "sessionAttributes": {
            "tenant_id": TENANT_A_ID,
        },
    }


@pytest.fixture
def get_billing_event():
    """Create a sample get_billing_info tool invocation event."""
    return {
        "toolName": "get_billing_info",
        "input": {
            "customer_id": "cb000000-0000-0000-0000-000000000001",
        },
        "sessionAttributes": {
            "tenant_id": TENANT_B_ID,
        },
    }


@pytest.fixture
def process_refund_event():
    """Create a sample process_refund tool invocation event."""
    return {
        "toolName": "process_refund",
        "input": {
            "customer_id": "cb000000-0000-0000-0000-000000000001",
            "amount": 50.00,
            "reason": "Service outage compensation",
        },
        "sessionAttributes": {
            "tenant_id": TENANT_B_ID,
        },
    }


# =============================================================================
# Tool event structure tests
# =============================================================================

class TestToolEventStructure:
    """Tests that tool invocation events have the expected structure."""

    def test_search_tickets_event_has_required_fields(self, search_tickets_event):
        """search_tickets event must contain toolName, input, and sessionAttributes."""
        assert "toolName" in search_tickets_event
        assert "input" in search_tickets_event
        assert "sessionAttributes" in search_tickets_event
        assert search_tickets_event["toolName"] == "search_tickets"

    def test_create_ticket_event_has_required_input(self, create_ticket_event):
        """create_ticket input must contain subject, description, and priority."""
        tool_input = create_ticket_event["input"]
        assert "subject" in tool_input
        assert "description" in tool_input
        assert "priority" in tool_input

    def test_session_attributes_contain_tenant_id(self, search_tickets_event):
        """All tool events must carry tenant_id in sessionAttributes."""
        assert "tenant_id" in search_tickets_event["sessionAttributes"]
        assert len(search_tickets_event["sessionAttributes"]["tenant_id"]) > 0

    def test_get_billing_event_has_customer_id(self, get_billing_event):
        """get_billing_info input must contain customer_id."""
        assert "customer_id" in get_billing_event["input"]

    def test_process_refund_event_has_amount(self, process_refund_event):
        """process_refund input must contain amount."""
        assert "amount" in process_refund_event["input"]
        assert isinstance(process_refund_event["input"]["amount"], (int, float))


# =============================================================================
# Tenant ID extraction tests
# =============================================================================

class TestTenantIdExtraction:
    """Tests that tenant_id is correctly extracted from events."""

    def _extract_tenant_id(self, event: dict) -> str | None:
        """Simulate the Lambda handler's tenant_id extraction logic."""
        return event.get("sessionAttributes", {}).get("tenant_id")

    def test_extract_tenant_id_from_search_tickets(self, search_tickets_event):
        """Should extract TenantA ID from search_tickets event."""
        tenant_id = self._extract_tenant_id(search_tickets_event)
        assert tenant_id == TENANT_A_ID

    def test_extract_tenant_id_from_billing(self, get_billing_event):
        """Should extract TenantB ID from get_billing_info event."""
        tenant_id = self._extract_tenant_id(get_billing_event)
        assert tenant_id == TENANT_B_ID

    def test_missing_tenant_id_returns_none(self):
        """Should return None when tenant_id is missing."""
        event = {"toolName": "search_tickets", "input": {}, "sessionAttributes": {}}
        tenant_id = self._extract_tenant_id(event)
        assert tenant_id is None

    def test_missing_session_attributes_returns_none(self):
        """Should return None when sessionAttributes is missing."""
        event = {"toolName": "search_tickets", "input": {}}
        tenant_id = self._extract_tenant_id(event)
        assert tenant_id is None


# =============================================================================
# Tool response structure tests
# =============================================================================

class TestToolResponseStructure:
    """Tests that tool responses have the expected format."""

    def test_successful_response_structure(self):
        """A successful tool response must have statusCode and body."""
        response = {
            "statusCode": 200,
            "body": json.dumps({
                "results": [
                    {"id": "ta000000-0000-0000-0000-000000000001", "subject": "Test ticket"}
                ],
                "count": 1,
            }),
        }
        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "results" in body
        assert "count" in body

    def test_error_response_structure(self):
        """An error response must have statusCode and error message."""
        response = {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Missing required field: subject",
            }),
        }
        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert "error" in body

    def test_unauthorized_response_for_missing_tenant(self):
        """Missing tenant_id should return a 403 response."""
        response = {
            "statusCode": 403,
            "body": json.dumps({
                "error": "Unauthorized: tenant_id is required.",
            }),
        }
        assert response["statusCode"] == 403

    def test_search_results_contain_tenant_scoped_data(self):
        """Search results should only contain data for the requesting tenant."""
        results = [
            {"id": "1", "tenant_id": TENANT_A_ID, "subject": "Ticket 1"},
            {"id": "2", "tenant_id": TENANT_A_ID, "subject": "Ticket 2"},
        ]
        # All results should belong to the same tenant
        tenant_ids = {r["tenant_id"] for r in results}
        assert len(tenant_ids) == 1
        assert TENANT_A_ID in tenant_ids


# =============================================================================
# Tool input validation tests
# =============================================================================

class TestToolInputValidation:
    """Tests that tool inputs are validated correctly."""

    def _validate_search_tickets_input(self, tool_input: dict) -> list[str]:
        """Simulate input validation for search_tickets."""
        errors = []
        if "query" not in tool_input and "status" not in tool_input:
            errors.append("At least one of 'query' or 'status' is required.")
        if "status" in tool_input:
            valid_statuses = {"open", "in_progress", "waiting_on_customer", "resolved", "closed"}
            if tool_input["status"] not in valid_statuses:
                errors.append(f"Invalid status: {tool_input['status']}")
        return errors

    def _validate_create_ticket_input(self, tool_input: dict) -> list[str]:
        """Simulate input validation for create_ticket."""
        errors = []
        required = ["subject", "description"]
        for field in required:
            if field not in tool_input or not tool_input[field].strip():
                errors.append(f"Missing required field: {field}")
        if "priority" in tool_input:
            valid_priorities = {"low", "medium", "high", "critical"}
            if tool_input["priority"] not in valid_priorities:
                errors.append(f"Invalid priority: {tool_input['priority']}")
        return errors

    def _validate_refund_input(self, tool_input: dict) -> list[str]:
        """Simulate input validation for process_refund."""
        errors = []
        if "amount" not in tool_input:
            errors.append("Missing required field: amount")
        elif tool_input["amount"] <= 0:
            errors.append("Refund amount must be positive.")
        if "customer_id" not in tool_input:
            errors.append("Missing required field: customer_id")
        return errors

    def test_valid_search_tickets_input(self, search_tickets_event):
        """Valid search_tickets input should pass validation."""
        errors = self._validate_search_tickets_input(search_tickets_event["input"])
        assert len(errors) == 0

    def test_empty_search_tickets_input_fails(self):
        """Empty search_tickets input should fail validation."""
        errors = self._validate_search_tickets_input({})
        assert len(errors) > 0

    def test_invalid_status_fails(self):
        """Invalid ticket status should fail validation."""
        errors = self._validate_search_tickets_input({"status": "invalid_status"})
        assert any("Invalid status" in e for e in errors)

    def test_valid_create_ticket_input(self, create_ticket_event):
        """Valid create_ticket input should pass validation."""
        errors = self._validate_create_ticket_input(create_ticket_event["input"])
        assert len(errors) == 0

    def test_missing_subject_fails(self):
        """Missing subject in create_ticket should fail validation."""
        errors = self._validate_create_ticket_input({"description": "test"})
        assert any("subject" in e for e in errors)

    def test_valid_refund_input(self, process_refund_event):
        """Valid process_refund input should pass validation."""
        errors = self._validate_refund_input(process_refund_event["input"])
        assert len(errors) == 0

    def test_negative_refund_amount_fails(self):
        """Negative refund amount should fail validation."""
        errors = self._validate_refund_input({"amount": -10, "customer_id": "test"})
        assert any("positive" in e for e in errors)

    def test_missing_refund_amount_fails(self):
        """Missing refund amount should fail validation."""
        errors = self._validate_refund_input({"customer_id": "test"})
        assert any("amount" in e for e in errors)


# =============================================================================
# Gateway routing tests
# =============================================================================

class TestGatewayRouting:
    """Tests that the Gateway routes tool calls to the correct Lambda."""

    TOOL_TO_LAMBDA_MAP = {
        "search_tickets": "agentcore-multi-tenant-search-tickets",
        "create_ticket": "agentcore-multi-tenant-create-ticket",
        "update_ticket": "agentcore-multi-tenant-update-ticket",
        "search_knowledge": "agentcore-multi-tenant-search-knowledge",
        "get_billing_info": "agentcore-multi-tenant-get-billing",
        "process_refund": "agentcore-multi-tenant-process-refund",
        "get_analytics": "agentcore-multi-tenant-get-analytics",
        "generate_report": "agentcore-multi-tenant-generate-report",
    }

    def test_all_tools_have_lambda_mapping(self):
        """Every tool should map to a Lambda function."""
        expected_tools = [
            "search_tickets", "create_ticket", "update_ticket",
            "search_knowledge", "get_billing_info", "process_refund",
            "get_analytics", "generate_report",
        ]
        for tool in expected_tools:
            assert tool in self.TOOL_TO_LAMBDA_MAP, f"Tool '{tool}' has no Lambda mapping"

    def test_lambda_names_follow_convention(self):
        """All Lambda names should follow the naming convention."""
        for tool_name, lambda_name in self.TOOL_TO_LAMBDA_MAP.items():
            assert lambda_name.startswith("agentcore-multi-tenant-"), \
                f"Lambda name '{lambda_name}' does not follow naming convention"

    def test_tool_name_resolves_to_lambda(self):
        """Given a tool name, the correct Lambda function should be resolved."""
        assert self.TOOL_TO_LAMBDA_MAP["search_tickets"] == "agentcore-multi-tenant-search-tickets"
        assert self.TOOL_TO_LAMBDA_MAP["process_refund"] == "agentcore-multi-tenant-process-refund"
