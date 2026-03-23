// =============================================================================
// Tenant Isolation Policy
// =============================================================================
// This policy enforces strict tenant isolation in the multi-tenant SaaS
// customer support agent. It ensures that a principal (user/agent) can only
// access resources belonging to their own tenant.
//
// The tenant_id is propagated through the request context and must match
// the principal's custom:tenantId attribute set during authentication.
// =============================================================================

// -----------------------------------------------------------------------------
// Rule: Permit access when the request's tenant_id matches the principal's
//       tenantId. This is the foundational isolation rule that applies to
//       ALL tool actions. Without a matching tenant_id, no access is granted.
// -----------------------------------------------------------------------------
permit (
    principal,
    action,
    resource
)
when {
    // The tenant_id passed in the request context must match
    // the tenantId attribute stored on the authenticated principal.
    context.tenant_id == principal.custom.tenantId
};

// -----------------------------------------------------------------------------
// Rule: Explicitly forbid access when tenant_id does NOT match.
// This acts as a safety net to deny cross-tenant access attempts even if
// other policies might inadvertently permit them.
// -----------------------------------------------------------------------------
forbid (
    principal,
    action,
    resource
)
when {
    context.tenant_id != principal.custom.tenantId
};

// -----------------------------------------------------------------------------
// Rule: Forbid access if tenant_id is missing from the request context.
// Every request MUST include a tenant_id; requests without one are denied.
// -----------------------------------------------------------------------------
forbid (
    principal,
    action,
    resource
)
unless {
    context has tenant_id
};
