#!/usr/bin/env python3
"""
Pytest tests for Cedar policy logic.

Tests verify that the Cedar policies enforce:
  - Tenant isolation (matching tenant_id required).
  - Tool access based on plan tier (Basic vs Premium).
  - Refund limits based on plan tier.

Since Cedar evaluation is done server-side, these tests simulate the
policy logic in Python to validate the intent of each rule.
"""

import pytest


# =============================================================================
# Constants
# =============================================================================

TENANT_A_ID = "tenant-a"
TENANT_B_ID = "tenant-b"

# Tool action names
TICKET_TOOLS = {"search_tickets", "create_ticket", "update_ticket"}
KNOWLEDGE_TOOLS = {"search_knowledge"}
BILLING_TOOLS = {"get_billing_info", "process_refund"}
ANALYTICS_TOOLS = {"get_analytics", "generate_report"}
ALL_TOOLS = TICKET_TOOLS | KNOWLEDGE_TOOLS | BILLING_TOOLS | ANALYTICS_TOOLS

# Plan-based tool access
BASIC_ALLOWED_TOOLS = TICKET_TOOLS | KNOWLEDGE_TOOLS
PREMIUM_ALLOWED_TOOLS = ALL_TOOLS

# Refund limits (in cents)
BASIC_REFUND_LIMIT = 10000    # $100
PREMIUM_REFUND_LIMIT = 100000  # $1000


# =============================================================================
# Policy simulation helpers
# =============================================================================

def evaluate_tenant_isolation(
    principal_tenant_id: str,
    request_tenant_id: str | None,
) -> str:
    """
    Simulate the tenant_isolation.cedar policy.
    Returns "ALLOW" or "DENY".
    """
    if request_tenant_id is None:
        return "DENY"
    if request_tenant_id != principal_tenant_id:
        return "DENY"
    return "ALLOW"


def evaluate_tool_access(
    plan: str,
    action: str,
) -> str:
    """
    Simulate the tool_access.cedar policy.
    Returns "ALLOW" or "DENY".
    """
    if plan == "basic":
        return "ALLOW" if action in BASIC_ALLOWED_TOOLS else "DENY"
    elif plan == "premium":
        return "ALLOW" if action in PREMIUM_ALLOWED_TOOLS else "DENY"
    return "DENY"


def evaluate_refund_limit(
    plan: str,
    refund_amount_cents: int | None,
) -> str:
    """
    Simulate the refund_limit.cedar policy.
    Returns "ALLOW" or "DENY".
    """
    if refund_amount_cents is None:
        return "DENY"

    if plan == "basic":
        return "ALLOW" if refund_amount_cents <= BASIC_REFUND_LIMIT else "DENY"
    elif plan == "premium":
        return "ALLOW" if refund_amount_cents <= PREMIUM_REFUND_LIMIT else "DENY"
    return "DENY"


# =============================================================================
# Tenant isolation policy tests
# =============================================================================

class TestTenantIsolationPolicy:
    """Tests for tenant_isolation.cedar policy logic."""

    def test_allow_matching_tenant_id(self):
        """Access should be ALLOWED when request tenant_id matches principal."""
        result = evaluate_tenant_isolation(TENANT_A_ID, TENANT_A_ID)
        assert result == "ALLOW"

    def test_deny_mismatched_tenant_id(self):
        """Access should be DENIED when tenant_ids do not match."""
        result = evaluate_tenant_isolation(TENANT_A_ID, TENANT_B_ID)
        assert result == "DENY"

    def test_deny_missing_tenant_id(self):
        """Access should be DENIED when tenant_id is missing from request."""
        result = evaluate_tenant_isolation(TENANT_A_ID, None)
        assert result == "DENY"

    def test_deny_empty_tenant_id(self):
        """Access should be DENIED when tenant_id is empty."""
        result = evaluate_tenant_isolation(TENANT_A_ID, "")
        assert result == "DENY"

    def test_both_tenants_can_access_own_data(self):
        """Both TenantA and TenantB should access their own data."""
        assert evaluate_tenant_isolation(TENANT_A_ID, TENANT_A_ID) == "ALLOW"
        assert evaluate_tenant_isolation(TENANT_B_ID, TENANT_B_ID) == "ALLOW"

    def test_cross_tenant_access_denied_both_directions(self):
        """Cross-tenant access should be denied in both directions."""
        assert evaluate_tenant_isolation(TENANT_A_ID, TENANT_B_ID) == "DENY"
        assert evaluate_tenant_isolation(TENANT_B_ID, TENANT_A_ID) == "DENY"


# =============================================================================
# Tool access policy tests
# =============================================================================

class TestToolAccessPolicy:
    """Tests for tool_access.cedar policy logic."""

    # --- Basic plan ---

    def test_basic_can_access_ticket_tools(self):
        """Basic plan should have access to all ticket tools."""
        for tool in TICKET_TOOLS:
            assert evaluate_tool_access("basic", tool) == "ALLOW", \
                f"Basic plan should access {tool}"

    def test_basic_can_access_knowledge_tools(self):
        """Basic plan should have access to knowledge tools."""
        for tool in KNOWLEDGE_TOOLS:
            assert evaluate_tool_access("basic", tool) == "ALLOW", \
                f"Basic plan should access {tool}"

    def test_basic_cannot_access_billing_tools(self):
        """Basic plan should NOT have access to billing tools."""
        for tool in BILLING_TOOLS:
            assert evaluate_tool_access("basic", tool) == "DENY", \
                f"Basic plan should not access {tool}"

    def test_basic_cannot_access_analytics_tools(self):
        """Basic plan should NOT have access to analytics tools."""
        for tool in ANALYTICS_TOOLS:
            assert evaluate_tool_access("basic", tool) == "DENY", \
                f"Basic plan should not access {tool}"

    # --- Premium plan ---

    def test_premium_can_access_all_tools(self):
        """Premium plan should have access to all tools."""
        for tool in ALL_TOOLS:
            assert evaluate_tool_access("premium", tool) == "ALLOW", \
                f"Premium plan should access {tool}"

    def test_premium_can_access_billing_tools(self):
        """Premium plan should have access to billing tools."""
        for tool in BILLING_TOOLS:
            assert evaluate_tool_access("premium", tool) == "ALLOW"

    def test_premium_can_access_analytics_tools(self):
        """Premium plan should have access to analytics tools."""
        for tool in ANALYTICS_TOOLS:
            assert evaluate_tool_access("premium", tool) == "ALLOW"

    # --- Unknown plan ---

    def test_unknown_plan_denied_all_tools(self):
        """An unknown plan should be denied access to all tools."""
        for tool in ALL_TOOLS:
            assert evaluate_tool_access("unknown", tool) == "DENY"

    # --- Count verification ---

    def test_basic_tool_count(self):
        """Basic plan should have access to exactly 4 tools."""
        allowed = [t for t in ALL_TOOLS if evaluate_tool_access("basic", t) == "ALLOW"]
        assert len(allowed) == 4  # 3 ticket + 1 knowledge

    def test_premium_tool_count(self):
        """Premium plan should have access to all 8 tools."""
        allowed = [t for t in ALL_TOOLS if evaluate_tool_access("premium", t) == "ALLOW"]
        assert len(allowed) == 8


# =============================================================================
# Refund limit policy tests
# =============================================================================

class TestRefundLimitPolicy:
    """Tests for refund_limit.cedar policy logic."""

    # --- Basic plan ---

    def test_basic_refund_within_limit(self):
        """Basic plan refund of $50 (5000 cents) should be allowed."""
        assert evaluate_refund_limit("basic", 5000) == "ALLOW"

    def test_basic_refund_at_limit(self):
        """Basic plan refund of exactly $100 (10000 cents) should be allowed."""
        assert evaluate_refund_limit("basic", 10000) == "ALLOW"

    def test_basic_refund_over_limit(self):
        """Basic plan refund of $101 (10100 cents) should be denied."""
        assert evaluate_refund_limit("basic", 10100) == "DENY"

    def test_basic_refund_well_over_limit(self):
        """Basic plan refund of $500 (50000 cents) should be denied."""
        assert evaluate_refund_limit("basic", 50000) == "DENY"

    # --- Premium plan ---

    def test_premium_refund_within_limit(self):
        """Premium plan refund of $500 (50000 cents) should be allowed."""
        assert evaluate_refund_limit("premium", 50000) == "ALLOW"

    def test_premium_refund_at_limit(self):
        """Premium plan refund of exactly $1000 (100000 cents) should be allowed."""
        assert evaluate_refund_limit("premium", 100000) == "ALLOW"

    def test_premium_refund_over_limit(self):
        """Premium plan refund of $1001 (100100 cents) should be denied."""
        assert evaluate_refund_limit("premium", 100100) == "DENY"

    def test_premium_refund_well_over_limit(self):
        """Premium plan refund of $5000 (500000 cents) should be denied."""
        assert evaluate_refund_limit("premium", 500000) == "DENY"

    # --- Edge cases ---

    def test_refund_without_amount_denied(self):
        """Refund without an amount should be denied."""
        assert evaluate_refund_limit("basic", None) == "DENY"
        assert evaluate_refund_limit("premium", None) == "DENY"

    def test_zero_refund_allowed(self):
        """A $0 refund should be allowed (edge case)."""
        assert evaluate_refund_limit("basic", 0) == "ALLOW"
        assert evaluate_refund_limit("premium", 0) == "ALLOW"

    def test_one_cent_refund_allowed(self):
        """A $0.01 refund (1 cent) should be allowed."""
        assert evaluate_refund_limit("basic", 1) == "ALLOW"
        assert evaluate_refund_limit("premium", 1) == "ALLOW"

    def test_unknown_plan_refund_denied(self):
        """Unknown plan should be denied any refund."""
        assert evaluate_refund_limit("unknown", 100) == "DENY"


# =============================================================================
# Combined policy evaluation tests
# =============================================================================

class TestCombinedPolicyEvaluation:
    """Tests that combine multiple policies for end-to-end authorization."""

    def evaluate_all_policies(
        self,
        principal_tenant_id: str,
        request_tenant_id: str | None,
        plan: str,
        action: str,
        refund_amount_cents: int | None = None,
    ) -> str:
        """
        Evaluate all policies in sequence.
        All must ALLOW for the final result to be ALLOW.
        """
        # 1. Tenant isolation
        if evaluate_tenant_isolation(principal_tenant_id, request_tenant_id) == "DENY":
            return "DENY"

        # 2. Tool access
        if evaluate_tool_access(plan, action) == "DENY":
            return "DENY"

        # 3. Refund limit (only for process_refund)
        if action == "process_refund":
            if evaluate_refund_limit(plan, refund_amount_cents) == "DENY":
                return "DENY"

        return "ALLOW"

    def test_basic_user_search_own_tickets(self):
        """Basic plan user searching own tickets should be allowed."""
        result = self.evaluate_all_policies(
            principal_tenant_id=TENANT_A_ID,
            request_tenant_id=TENANT_A_ID,
            plan="basic",
            action="search_tickets",
        )
        assert result == "ALLOW"

    def test_basic_user_access_billing_denied(self):
        """Basic plan user accessing billing should be denied."""
        result = self.evaluate_all_policies(
            principal_tenant_id=TENANT_A_ID,
            request_tenant_id=TENANT_A_ID,
            plan="basic",
            action="get_billing_info",
        )
        assert result == "DENY"

    def test_basic_user_small_refund_denied_by_tool_access(self):
        """Basic plan user cannot process refunds (tool access denied)."""
        result = self.evaluate_all_policies(
            principal_tenant_id=TENANT_A_ID,
            request_tenant_id=TENANT_A_ID,
            plan="basic",
            action="process_refund",
            refund_amount_cents=5000,
        )
        assert result == "DENY"

    def test_premium_user_search_own_tickets(self):
        """Premium plan user searching own tickets should be allowed."""
        result = self.evaluate_all_policies(
            principal_tenant_id=TENANT_B_ID,
            request_tenant_id=TENANT_B_ID,
            plan="premium",
            action="search_tickets",
        )
        assert result == "ALLOW"

    def test_premium_user_small_refund_allowed(self):
        """Premium plan user processing a $50 refund should be allowed."""
        result = self.evaluate_all_policies(
            principal_tenant_id=TENANT_B_ID,
            request_tenant_id=TENANT_B_ID,
            plan="premium",
            action="process_refund",
            refund_amount_cents=5000,
        )
        assert result == "ALLOW"

    def test_premium_user_large_refund_denied(self):
        """Premium plan user processing a $1500 refund should be denied."""
        result = self.evaluate_all_policies(
            principal_tenant_id=TENANT_B_ID,
            request_tenant_id=TENANT_B_ID,
            plan="premium",
            action="process_refund",
            refund_amount_cents=150000,
        )
        assert result == "DENY"

    def test_cross_tenant_premium_denied(self):
        """Even Premium users cannot access another tenant's data."""
        result = self.evaluate_all_policies(
            principal_tenant_id=TENANT_B_ID,
            request_tenant_id=TENANT_A_ID,
            plan="premium",
            action="search_tickets",
        )
        assert result == "DENY"

    def test_missing_tenant_id_always_denied(self):
        """Missing tenant_id should deny access regardless of plan or action."""
        for plan in ("basic", "premium"):
            for action in ALL_TOOLS:
                result = self.evaluate_all_policies(
                    principal_tenant_id=TENANT_A_ID,
                    request_tenant_id=None,
                    plan=plan,
                    action=action,
                )
                assert result == "DENY", \
                    f"Missing tenant_id should deny {plan}/{action}"
