-- =============================================================================
-- Row-Level Security (RLS) Policies for Multi-Tenant Isolation
-- =============================================================================
-- These policies enforce tenant isolation at the database level.
-- Each query must set the application context variable 'app.current_tenant_id'
-- before accessing any table. Only rows matching the current tenant are visible.
--
-- Usage in application code (per-request):
--   SET app.current_tenant_id = 'tenant-a';
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Application role for Lambda handlers
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user LOGIN;
    END IF;
END
$$;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- =============================================================================
-- Enable RLS on all tenant-scoped tables
-- =============================================================================

ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE billing_records ENABLE ROW LEVEL SECURITY;

ALTER TABLE customers FORCE ROW LEVEL SECURITY;
ALTER TABLE support_tickets FORCE ROW LEVEL SECURITY;
ALTER TABLE knowledge_articles FORCE ROW LEVEL SECURITY;
ALTER TABLE billing_records FORCE ROW LEVEL SECURITY;

-- =============================================================================
-- Customers table policies
-- =============================================================================

CREATE POLICY customers_select_policy ON customers
    FOR SELECT TO app_user
    USING (tenant_id = current_setting('app.current_tenant_id', true));

CREATE POLICY customers_insert_policy ON customers
    FOR INSERT TO app_user
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));

CREATE POLICY customers_update_policy ON customers
    FOR UPDATE TO app_user
    USING (tenant_id = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));

-- =============================================================================
-- Support Tickets table policies
-- =============================================================================

CREATE POLICY tickets_select_policy ON support_tickets
    FOR SELECT TO app_user
    USING (tenant_id = current_setting('app.current_tenant_id', true));

CREATE POLICY tickets_insert_policy ON support_tickets
    FOR INSERT TO app_user
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));

CREATE POLICY tickets_update_policy ON support_tickets
    FOR UPDATE TO app_user
    USING (tenant_id = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));

-- =============================================================================
-- Knowledge Articles table policies
-- =============================================================================

CREATE POLICY articles_select_policy ON knowledge_articles
    FOR SELECT TO app_user
    USING (tenant_id = current_setting('app.current_tenant_id', true));

CREATE POLICY articles_insert_policy ON knowledge_articles
    FOR INSERT TO app_user
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));

CREATE POLICY articles_update_policy ON knowledge_articles
    FOR UPDATE TO app_user
    USING (tenant_id = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));

-- =============================================================================
-- Billing Records table policies
-- =============================================================================

CREATE POLICY billing_select_policy ON billing_records
    FOR SELECT TO app_user
    USING (tenant_id = current_setting('app.current_tenant_id', true));

CREATE POLICY billing_insert_policy ON billing_records
    FOR INSERT TO app_user
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));

CREATE POLICY billing_update_policy ON billing_records
    FOR UPDATE TO app_user
    USING (tenant_id = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
