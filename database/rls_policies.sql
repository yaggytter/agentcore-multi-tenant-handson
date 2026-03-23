-- =============================================================================
-- Row-Level Security (RLS) Policies for Multi-Tenant Isolation
-- =============================================================================
-- These policies enforce tenant isolation at the database level.
-- Each query must set the application context variable 'app.current_tenant_id'
-- before accessing any table. Only rows matching the current tenant are visible.
--
-- Usage in application code (per-request):
--   SET app.current_tenant_id = '<tenant-uuid>';
--
-- This ensures that even if application-level authorization is bypassed,
-- the database itself enforces tenant boundaries.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Create an application role for the Lambda functions to use.
-- This role will have RLS applied; the superuser/owner bypasses RLS.
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user LOGIN;
    END IF;
END
$$;

-- Grant table access to the application role
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;

-- =============================================================================
-- Enable RLS on all tenant-scoped tables
-- =============================================================================

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_records ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- Tenants table policies
-- =============================================================================

-- SELECT: A tenant can only see its own record
CREATE POLICY tenants_select_policy ON tenants
    FOR SELECT
    TO app_user
    USING (id::text = current_setting('app.current_tenant_id', true));

-- INSERT: A tenant can only insert its own record
CREATE POLICY tenants_insert_policy ON tenants
    FOR INSERT
    TO app_user
    WITH CHECK (id::text = current_setting('app.current_tenant_id', true));

-- UPDATE: A tenant can only update its own record
CREATE POLICY tenants_update_policy ON tenants
    FOR UPDATE
    TO app_user
    USING (id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (id::text = current_setting('app.current_tenant_id', true));

-- =============================================================================
-- Customers table policies
-- =============================================================================

-- SELECT: Only see customers belonging to the current tenant
CREATE POLICY customers_select_policy ON customers
    FOR SELECT
    TO app_user
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

-- INSERT: Can only create customers for the current tenant
CREATE POLICY customers_insert_policy ON customers
    FOR INSERT
    TO app_user
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- UPDATE: Can only update customers belonging to the current tenant
CREATE POLICY customers_update_policy ON customers
    FOR UPDATE
    TO app_user
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- =============================================================================
-- Support Tickets table policies
-- =============================================================================

-- SELECT: Only see tickets belonging to the current tenant
CREATE POLICY tickets_select_policy ON support_tickets
    FOR SELECT
    TO app_user
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

-- INSERT: Can only create tickets for the current tenant
CREATE POLICY tickets_insert_policy ON support_tickets
    FOR INSERT
    TO app_user
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- UPDATE: Can only update tickets belonging to the current tenant
CREATE POLICY tickets_update_policy ON support_tickets
    FOR UPDATE
    TO app_user
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- =============================================================================
-- Knowledge Articles table policies
-- =============================================================================

-- SELECT: Only see articles belonging to the current tenant
CREATE POLICY articles_select_policy ON knowledge_articles
    FOR SELECT
    TO app_user
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

-- INSERT: Can only create articles for the current tenant
CREATE POLICY articles_insert_policy ON knowledge_articles
    FOR INSERT
    TO app_user
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- UPDATE: Can only update articles belonging to the current tenant
CREATE POLICY articles_update_policy ON knowledge_articles
    FOR UPDATE
    TO app_user
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- =============================================================================
-- Billing Records table policies
-- =============================================================================

-- SELECT: Only see billing records belonging to the current tenant
CREATE POLICY billing_select_policy ON billing_records
    FOR SELECT
    TO app_user
    USING (tenant_id::text = current_setting('app.current_tenant_id', true));

-- INSERT: Can only create billing records for the current tenant
CREATE POLICY billing_insert_policy ON billing_records
    FOR INSERT
    TO app_user
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));

-- UPDATE: Can only update billing records belonging to the current tenant
CREATE POLICY billing_update_policy ON billing_records
    FOR UPDATE
    TO app_user
    USING (tenant_id::text = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id::text = current_setting('app.current_tenant_id', true));
