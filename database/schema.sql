-- =============================================================================
-- PostgreSQL Schema for AgentCore Multi-Tenant Customer Support
-- =============================================================================
-- This schema supports a multi-tenant SaaS customer support agent.
-- All tables include a tenant_id column to enable row-level security (RLS)
-- and strict tenant isolation.
-- =============================================================================

-- Enable UUID extension for generating unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- Tenants table
-- Stores information about each tenant (organization) in the system.
-- -----------------------------------------------------------------------------
CREATE TABLE tenants (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) NOT NULL,
    plan        VARCHAR(50) NOT NULL CHECK (plan IN ('basic', 'premium')),
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tenants_plan ON tenants (plan);

COMMENT ON TABLE tenants IS 'Registered tenant organizations';
COMMENT ON COLUMN tenants.plan IS 'Subscription plan: basic or premium';

-- -----------------------------------------------------------------------------
-- Customers table
-- Stores customer records, each scoped to a specific tenant.
-- -----------------------------------------------------------------------------
CREATE TABLE customers (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    email       VARCHAR(255) NOT NULL,
    plan        VARCHAR(50) NOT NULL CHECK (plan IN ('free', 'starter', 'business', 'enterprise')),
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_customers_tenant_id ON customers (tenant_id);
CREATE INDEX idx_customers_email ON customers (email);
CREATE UNIQUE INDEX idx_customers_tenant_email ON customers (tenant_id, email);

COMMENT ON TABLE customers IS 'End-user customers belonging to a tenant';

-- -----------------------------------------------------------------------------
-- Support Tickets table
-- Stores support tickets filed by customers, scoped per tenant.
-- -----------------------------------------------------------------------------
CREATE TABLE support_tickets (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    subject     VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    status      VARCHAR(50) NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'in_progress', 'waiting_on_customer', 'resolved', 'closed')),
    priority    VARCHAR(20) NOT NULL DEFAULT 'medium'
                CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolution  TEXT
);

CREATE INDEX idx_tickets_tenant_id ON support_tickets (tenant_id);
CREATE INDEX idx_tickets_customer_id ON support_tickets (customer_id);
CREATE INDEX idx_tickets_status ON support_tickets (status);
CREATE INDEX idx_tickets_priority ON support_tickets (priority);
CREATE INDEX idx_tickets_tenant_status ON support_tickets (tenant_id, status);
CREATE INDEX idx_tickets_created_at ON support_tickets (created_at DESC);

COMMENT ON TABLE support_tickets IS 'Customer support tickets scoped per tenant';

-- -----------------------------------------------------------------------------
-- Knowledge Articles table
-- Stores knowledge base articles for self-service, scoped per tenant.
-- -----------------------------------------------------------------------------
CREATE TABLE knowledge_articles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title       VARCHAR(500) NOT NULL,
    content     TEXT NOT NULL,
    category    VARCHAR(100) NOT NULL,
    tags        TEXT[] DEFAULT '{}',
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_articles_tenant_id ON knowledge_articles (tenant_id);
CREATE INDEX idx_articles_category ON knowledge_articles (category);
CREATE INDEX idx_articles_tenant_category ON knowledge_articles (tenant_id, category);

COMMENT ON TABLE knowledge_articles IS 'Knowledge base articles scoped per tenant';

-- -----------------------------------------------------------------------------
-- Billing Records table
-- Stores billing and refund transactions, scoped per tenant.
-- -----------------------------------------------------------------------------
CREATE TABLE billing_records (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    amount      DECIMAL(10, 2) NOT NULL,
    type        VARCHAR(50) NOT NULL CHECK (type IN ('charge', 'refund', 'credit', 'adjustment')),
    status      VARCHAR(50) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'completed', 'failed', 'cancelled')),
    description TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_billing_tenant_id ON billing_records (tenant_id);
CREATE INDEX idx_billing_customer_id ON billing_records (customer_id);
CREATE INDEX idx_billing_type ON billing_records (type);
CREATE INDEX idx_billing_status ON billing_records (status);
CREATE INDEX idx_billing_tenant_customer ON billing_records (tenant_id, customer_id);

COMMENT ON TABLE billing_records IS 'Billing and refund records scoped per tenant';

-- -----------------------------------------------------------------------------
-- Updated-at trigger function
-- Automatically updates the updated_at timestamp on row modification.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tickets_updated_at
    BEFORE UPDATE ON support_tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_articles_updated_at
    BEFORE UPDATE ON knowledge_articles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
