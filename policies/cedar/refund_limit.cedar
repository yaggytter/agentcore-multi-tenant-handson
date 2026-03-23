// =============================================================================
// Refund Limit Policy
// =============================================================================
// This policy enforces per-refund amount limits based on the tenant's plan.
//
// Limits:
//   - Basic plan:   maximum $100 per refund
//   - Premium plan:  maximum $1000 per refund
//
// Refunds exceeding the plan limit are explicitly forbidden.
// The refund amount is expected in the request context as context.refund_amount
// (represented in cents to avoid floating-point issues, e.g., 10000 = $100).
// =============================================================================

// -----------------------------------------------------------------------------
// Basic Plan: Permit refunds up to $100 (10000 cents)
// Only allows the process_refund action when the amount is within the limit.
// -----------------------------------------------------------------------------
permit (
    principal,
    action == Tool::Action::"process_refund",
    resource
)
when {
    principal.custom.plan == "basic" &&
    context has refund_amount &&
    context.refund_amount <= 10000
};

// -----------------------------------------------------------------------------
// Basic Plan: Forbid refunds exceeding $100 (10000 cents)
// Any refund request over the Basic plan limit is denied.
// -----------------------------------------------------------------------------
forbid (
    principal,
    action == Tool::Action::"process_refund",
    resource
)
when {
    principal.custom.plan == "basic" &&
    context has refund_amount &&
    context.refund_amount > 10000
};

// -----------------------------------------------------------------------------
// Premium Plan: Permit refunds up to $1000 (100000 cents)
// Premium plan users can process higher-value refunds.
// -----------------------------------------------------------------------------
permit (
    principal,
    action == Tool::Action::"process_refund",
    resource
)
when {
    principal.custom.plan == "premium" &&
    context has refund_amount &&
    context.refund_amount <= 100000
};

// -----------------------------------------------------------------------------
// Premium Plan: Forbid refunds exceeding $1000 (100000 cents)
// Even Premium plan users cannot process refunds above the $1000 cap.
// -----------------------------------------------------------------------------
forbid (
    principal,
    action == Tool::Action::"process_refund",
    resource
)
when {
    principal.custom.plan == "premium" &&
    context has refund_amount &&
    context.refund_amount > 100000
};

// -----------------------------------------------------------------------------
// Forbid refunds without an amount specified
// Every refund request must include a refund_amount in the context.
// -----------------------------------------------------------------------------
forbid (
    principal,
    action == Tool::Action::"process_refund",
    resource
)
unless {
    context has refund_amount
};
