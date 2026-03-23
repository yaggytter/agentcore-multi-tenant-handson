"""
Schema Initialization Lambda for Aurora PostgreSQL.
Creates tables with Row-Level Security (RLS) for multi-tenant isolation.
Used as a CloudFormation Custom Resource via cr.Provider.
"""

import json
import boto3
import os


def handler(event, context):
    """
    Custom Resource handler to initialize Aurora PostgreSQL schema
    with Row-Level Security (RLS) for multi-tenant isolation.

    Returns a dict (cr.Provider handles the CloudFormation callback).
    """
    request_type = event.get("RequestType", "Create")

    if request_type == "Delete":
        return {
            "PhysicalResourceId": "schema-init",
            "Data": {"Message": "Nothing to delete"},
        }

    rds_client = boto3.client("rds-data")
    cluster_arn = os.environ["CLUSTER_ARN"]
    secret_arn = os.environ["SECRET_ARN"]
    database = os.environ["DATABASE_NAME"]

    # SQL statements to create schema with RLS
    statements = [
        # Extension for UUID generation
        "CREATE EXTENSION IF NOT EXISTS pgcrypto;",

        # Tenants table
        """
        CREATE TABLE IF NOT EXISTS tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) UNIQUE NOT NULL,
            name VARCHAR(256) NOT NULL,
            plan VARCHAR(32) NOT NULL DEFAULT 'standard',
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            domain VARCHAR(256),
            locale VARCHAR(8) DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,

        # Customers table
        """
        CREATE TABLE IF NOT EXISTS customers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id VARCHAR(64) NOT NULL,
            tenant_id VARCHAR(64) NOT NULL,
            name VARCHAR(256) NOT NULL,
            email VARCHAR(256),
            phone VARCHAR(64),
            plan VARCHAR(32),
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(customer_id, tenant_id)
        );
        """,

        # Support tickets table
        """
        CREATE TABLE IF NOT EXISTS support_tickets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            customer_id VARCHAR(64),
            ticket_id VARCHAR(64) UNIQUE NOT NULL,
            subject VARCHAR(512) NOT NULL,
            description TEXT,
            status VARCHAR(32) NOT NULL DEFAULT 'open',
            priority VARCHAR(16) NOT NULL DEFAULT 'medium',
            category VARCHAR(128),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP,
            resolution TEXT,
            assigned_to VARCHAR(256)
        );
        """,

        # Knowledge articles table
        """
        CREATE TABLE IF NOT EXISTS knowledge_articles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            article_id VARCHAR(64) UNIQUE NOT NULL,
            tenant_id VARCHAR(64) NOT NULL,
            title VARCHAR(512) NOT NULL,
            content TEXT NOT NULL,
            category VARCHAR(128),
            tags TEXT[],
            author VARCHAR(256),
            search_vector tsvector,
            view_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,

        # Billing records table
        """
        CREATE TABLE IF NOT EXISTS billing_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            customer_id VARCHAR(64),
            amount DECIMAL(12,2) NOT NULL,
            type VARCHAR(32),
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,

        # Billing info table (used by standalone Lambda handlers)
        """
        CREATE TABLE IF NOT EXISTS billing_info (
            billing_id VARCHAR(64) PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            customer_id VARCHAR(64) NOT NULL,
            plan_name VARCHAR(128),
            billing_cycle VARCHAR(32),
            amount DECIMAL(12,2) NOT NULL,
            currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            next_billing_date DATE,
            payment_method VARCHAR(64),
            status VARCHAR(32) NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,

        # Invoices table
        """
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id VARCHAR(64) PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            customer_id VARCHAR(64) NOT NULL,
            amount DECIMAL(12,2) NOT NULL,
            currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            invoice_date TIMESTAMP,
            due_date TIMESTAMP,
            paid_date TIMESTAMP,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            description TEXT
        );
        """,

        # Refunds table
        """
        CREATE TABLE IF NOT EXISTS refunds (
            refund_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            customer_id VARCHAR(64) NOT NULL,
            amount DECIMAL(12,2) NOT NULL,
            reason TEXT,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            processed_by VARCHAR(256),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,

        # Tenant-user mappings table
        """
        CREATE TABLE IF NOT EXISTS tenant_user_mappings (
            user_id VARCHAR(256) PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            tenant_name VARCHAR(256),
            tenant_plan VARCHAR(32),
            role VARCHAR(32) NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,

        # Agent conversation history
        """
        CREATE TABLE IF NOT EXISTS conversation_history (
            conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            session_id VARCHAR(128) NOT NULL,
            user_id VARCHAR(256) NOT NULL,
            role VARCHAR(16) NOT NULL,
            content TEXT NOT NULL,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,

        # Enable RLS on all tenant-scoped tables
        "ALTER TABLE customers ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE knowledge_articles ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE billing_records ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE billing_info ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE refunds ENABLE ROW LEVEL SECURITY;",
        "ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;",

        # Create application role for tenant-scoped access
        "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN CREATE ROLE app_user; END IF; END $$;",

        # RLS policies
        "DROP POLICY IF EXISTS tenant_isolation_customers ON customers;",
        """
        CREATE POLICY tenant_isolation_customers ON customers
            FOR ALL
            USING (tenant_id = current_setting('app.current_tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
        """,

        "DROP POLICY IF EXISTS tenant_isolation_tickets ON support_tickets;",
        """
        CREATE POLICY tenant_isolation_tickets ON support_tickets
            FOR ALL
            USING (tenant_id = current_setting('app.current_tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
        """,

        "DROP POLICY IF EXISTS tenant_isolation_articles ON knowledge_articles;",
        """
        CREATE POLICY tenant_isolation_articles ON knowledge_articles
            FOR ALL
            USING (tenant_id = current_setting('app.current_tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
        """,

        "DROP POLICY IF EXISTS tenant_isolation_billing ON billing_records;",
        """
        CREATE POLICY tenant_isolation_billing ON billing_records
            FOR ALL
            USING (tenant_id = current_setting('app.current_tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
        """,

        "DROP POLICY IF EXISTS tenant_isolation_billing_info ON billing_info;",
        """
        CREATE POLICY tenant_isolation_billing_info ON billing_info
            FOR ALL
            USING (tenant_id = current_setting('app.current_tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
        """,

        "DROP POLICY IF EXISTS tenant_isolation_invoices ON invoices;",
        """
        CREATE POLICY tenant_isolation_invoices ON invoices
            FOR ALL
            USING (tenant_id = current_setting('app.current_tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
        """,

        "DROP POLICY IF EXISTS tenant_isolation_refunds ON refunds;",
        """
        CREATE POLICY tenant_isolation_refunds ON refunds
            FOR ALL
            USING (tenant_id = current_setting('app.current_tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
        """,

        "DROP POLICY IF EXISTS tenant_isolation_conversations ON conversation_history;",
        """
        CREATE POLICY tenant_isolation_conversations ON conversation_history
            FOR ALL
            USING (tenant_id = current_setting('app.current_tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));
        """,

        # Grant permissions to app_user role
        "GRANT SELECT, INSERT, UPDATE, DELETE ON customers TO app_user;",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON support_tickets TO app_user;",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON knowledge_articles TO app_user;",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON billing_records TO app_user;",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON billing_info TO app_user;",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON invoices TO app_user;",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON refunds TO app_user;",
        "GRANT SELECT, INSERT, UPDATE, DELETE ON conversation_history TO app_user;",
        "GRANT SELECT ON tenants TO app_user;",

        # Create indexes for tenant_id lookups
        "CREATE INDEX IF NOT EXISTS idx_customers_tenant ON customers(tenant_id);",
        "CREATE INDEX IF NOT EXISTS idx_tickets_tenant ON support_tickets(tenant_id);",
        "CREATE INDEX IF NOT EXISTS idx_articles_tenant ON knowledge_articles(tenant_id);",
        "CREATE INDEX IF NOT EXISTS idx_billing_tenant ON billing_records(tenant_id);",
        "CREATE INDEX IF NOT EXISTS idx_billing_info_tenant ON billing_info(tenant_id);",
        "CREATE INDEX IF NOT EXISTS idx_invoices_tenant ON invoices(tenant_id);",
        "CREATE INDEX IF NOT EXISTS idx_refunds_tenant ON refunds(tenant_id);",
        "CREATE INDEX IF NOT EXISTS idx_conversations_tenant ON conversation_history(tenant_id);",

        # Full-text search index for knowledge articles
        """
        CREATE INDEX IF NOT EXISTS idx_articles_search
            ON knowledge_articles USING gin(search_vector);
        """,

        # Trigger to auto-update search_vector on knowledge_articles
        """
        CREATE OR REPLACE FUNCTION update_search_vector()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('simple', COALESCE(NEW.title, '') || ' ' || COALESCE(NEW.content, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """,

        "DROP TRIGGER IF EXISTS trg_update_search_vector ON knowledge_articles;",
        """
        CREATE TRIGGER trg_update_search_vector
            BEFORE INSERT OR UPDATE ON knowledge_articles
            FOR EACH ROW EXECUTE FUNCTION update_search_vector();
        """,

        # Seed demo tenants
        """
        INSERT INTO tenants (tenant_id, name, plan, status, domain, locale)
        VALUES
            ('tenant-a', 'Acme Corp', 'enterprise', 'active', 'acme-corp.example.com', 'ja'),
            ('tenant-b', 'GlobalTech', 'professional', 'active', 'globaltech.example.com', 'en')
        ON CONFLICT (tenant_id) DO NOTHING;
        """,
    ]

    for sql in statements:
        rds_client.execute_statement(
            resourceArn=cluster_arn,
            secretArn=secret_arn,
            database=database,
            sql=sql.strip(),
        )

    return {
        "PhysicalResourceId": "schema-init",
        "Data": {"Message": "Schema initialized successfully"},
    }
