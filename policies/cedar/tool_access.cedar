// =============================================================================
// Tool Access Control Policy
// =============================================================================
// This policy controls which tools each tenant plan tier can access.
//
// Plan tiers:
//   - Basic:   access to ticket and knowledge tools only
//   - Premium: access to all tools (ticket, knowledge, billing, analytics)
//
// Tool actions are defined as:
//   - Tool::Action::"search_tickets"
//   - Tool::Action::"create_ticket"
//   - Tool::Action::"update_ticket"
//   - Tool::Action::"search_knowledge"
//   - Tool::Action::"get_billing_info"
//   - Tool::Action::"process_refund"
//   - Tool::Action::"get_analytics"
//   - Tool::Action::"generate_report"
// =============================================================================

// -----------------------------------------------------------------------------
// Basic Plan: Permit access to ticket management tools
// Users on the Basic plan can search, create, and update support tickets.
// -----------------------------------------------------------------------------
permit (
    principal,
    action in [
        Tool::Action::"search_tickets",
        Tool::Action::"create_ticket",
        Tool::Action::"update_ticket"
    ],
    resource
)
when {
    principal.custom.plan == "basic"
};

// -----------------------------------------------------------------------------
// Basic Plan: Permit access to knowledge base tools
// Users on the Basic plan can search the knowledge base for articles.
// -----------------------------------------------------------------------------
permit (
    principal,
    action in [
        Tool::Action::"search_knowledge"
    ],
    resource
)
when {
    principal.custom.plan == "basic"
};

// -----------------------------------------------------------------------------
// Basic Plan: Explicitly forbid access to billing tools
// Users on the Basic plan cannot access billing or refund functionality.
// -----------------------------------------------------------------------------
forbid (
    principal,
    action in [
        Tool::Action::"get_billing_info",
        Tool::Action::"process_refund"
    ],
    resource
)
when {
    principal.custom.plan == "basic"
};

// -----------------------------------------------------------------------------
// Basic Plan: Explicitly forbid access to analytics tools
// Users on the Basic plan cannot access analytics or reporting.
// -----------------------------------------------------------------------------
forbid (
    principal,
    action in [
        Tool::Action::"get_analytics",
        Tool::Action::"generate_report"
    ],
    resource
)
when {
    principal.custom.plan == "basic"
};

// -----------------------------------------------------------------------------
// Premium Plan: Permit access to ALL tools
// Users on the Premium plan have unrestricted tool access, including
// ticket management, knowledge base, billing, and analytics.
// -----------------------------------------------------------------------------
permit (
    principal,
    action in [
        Tool::Action::"search_tickets",
        Tool::Action::"create_ticket",
        Tool::Action::"update_ticket",
        Tool::Action::"search_knowledge",
        Tool::Action::"get_billing_info",
        Tool::Action::"process_refund",
        Tool::Action::"get_analytics",
        Tool::Action::"generate_report"
    ],
    resource
)
when {
    principal.custom.plan == "premium"
};
