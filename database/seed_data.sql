-- =============================================================================
-- Seed Data for AgentCore Multi-Tenant Customer Support
-- =============================================================================
-- Populates the database with test data for two tenants:
--   - TenantA: Acme Corp (Basic plan)
--   - TenantB: GlobalTech (Premium plan)
--
-- Each tenant gets:
--   - 5 customers
--   - 10 support tickets (various statuses)
--   - 5 knowledge articles
--   - 10 billing records
-- =============================================================================

-- Use fixed UUIDs for reproducibility in testing
-- TenantA: Acme Corp
-- TenantB: GlobalTech

-- -----------------------------------------------------------------------------
-- Tenants
-- -----------------------------------------------------------------------------
INSERT INTO tenants (id, name, plan) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'Acme Corp', 'basic'),
    ('b0000000-0000-0000-0000-000000000001', 'GlobalTech', 'premium');

-- -----------------------------------------------------------------------------
-- Customers - TenantA (Acme Corp)
-- -----------------------------------------------------------------------------
INSERT INTO customers (id, tenant_id, name, email, plan) VALUES
    ('ca000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'Alice Johnson', 'alice@acmecorp.example.com', 'starter'),
    ('ca000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'Bob Smith', 'bob@acmecorp.example.com', 'business'),
    ('ca000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001', 'Carol Williams', 'carol@acmecorp.example.com', 'free'),
    ('ca000000-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000001', 'David Brown', 'david@acmecorp.example.com', 'starter'),
    ('ca000000-0000-0000-0000-000000000005', 'a0000000-0000-0000-0000-000000000001', 'Eve Davis', 'eve@acmecorp.example.com', 'business');

-- -----------------------------------------------------------------------------
-- Customers - TenantB (GlobalTech)
-- -----------------------------------------------------------------------------
INSERT INTO customers (id, tenant_id, name, email, plan) VALUES
    ('cb000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'Frank Miller', 'frank@globaltech.example.com', 'business'),
    ('cb000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000001', 'Grace Wilson', 'grace@globaltech.example.com', 'enterprise'),
    ('cb000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000001', 'Hank Moore', 'hank@globaltech.example.com', 'starter'),
    ('cb000000-0000-0000-0000-000000000004', 'b0000000-0000-0000-0000-000000000001', 'Ivy Taylor', 'ivy@globaltech.example.com', 'enterprise'),
    ('cb000000-0000-0000-0000-000000000005', 'b0000000-0000-0000-0000-000000000001', 'Jack Anderson', 'jack@globaltech.example.com', 'business');

-- -----------------------------------------------------------------------------
-- Support Tickets - TenantA (Acme Corp) - 10 tickets
-- -----------------------------------------------------------------------------
INSERT INTO support_tickets (id, tenant_id, customer_id, subject, description, status, priority, resolution) VALUES
    ('ta000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000001',
     'Cannot login to dashboard', 'I am unable to log in to my dashboard. The page shows a 403 error after entering credentials.', 'open', 'high', NULL),
    ('ta000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000002',
     'Billing discrepancy on last invoice', 'The amount on my latest invoice does not match the quoted price.', 'in_progress', 'medium', NULL),
    ('ta000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000003',
     'Feature request: dark mode', 'It would be great to have a dark mode option in the application.', 'open', 'low', NULL),
    ('ta000000-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000004',
     'API rate limiting issues', 'We are hitting rate limits during peak hours. Can the quota be increased?', 'waiting_on_customer', 'high', NULL),
    ('ta000000-0000-0000-0000-000000000005', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000005',
     'Data export not working', 'The CSV export feature returns an empty file for reports over 10,000 rows.', 'in_progress', 'critical', NULL),
    ('ta000000-0000-0000-0000-000000000006', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000001',
     'Password reset email not received', 'I requested a password reset 30 minutes ago but have not received the email.', 'resolved', 'medium',
     'The email was caught by the spam filter. Whitelisting instructions were provided.'),
    ('ta000000-0000-0000-0000-000000000007', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000002',
     'Integration with Slack failing', 'The Slack integration stopped working after updating to v2.3.', 'open', 'high', NULL),
    ('ta000000-0000-0000-0000-000000000008', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000003',
     'Account upgrade request', 'I would like to upgrade my free account to a starter plan.', 'closed', 'low',
     'Account upgraded successfully to starter plan.'),
    ('ta000000-0000-0000-0000-000000000009', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000004',
     'Slow page load times', 'Dashboard pages are taking over 10 seconds to load since last week.', 'in_progress', 'high', NULL),
    ('ta000000-0000-0000-0000-000000000010', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000005',
     'Webhook delivery failures', 'Webhooks to our endpoint are failing with timeout errors.', 'resolved', 'medium',
     'Increased webhook timeout to 30 seconds and added retry logic.');

-- -----------------------------------------------------------------------------
-- Support Tickets - TenantB (GlobalTech) - 10 tickets
-- -----------------------------------------------------------------------------
INSERT INTO support_tickets (id, tenant_id, customer_id, subject, description, status, priority, resolution) VALUES
    ('tb000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000001',
     'SSO configuration help needed', 'We need assistance configuring SAML SSO with our Okta instance.', 'open', 'high', NULL),
    ('tb000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000002',
     'Custom report template', 'Can we create custom report templates for our quarterly review?', 'in_progress', 'medium', NULL),
    ('tb000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000003',
     'Mobile app crash on Android 14', 'The mobile app crashes immediately on launch on Pixel 8 running Android 14.', 'open', 'critical', NULL),
    ('tb000000-0000-0000-0000-000000000004', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000004',
     'Bulk user import failing', 'Importing 5000+ users via CSV fails with a generic error message.', 'in_progress', 'high', NULL),
    ('tb000000-0000-0000-0000-000000000005', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000005',
     'Request for API documentation update', 'The v3 API documentation is missing the new pagination parameters.', 'waiting_on_customer', 'low', NULL),
    ('tb000000-0000-0000-0000-000000000006', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000001',
     'Data retention policy question', 'What is the data retention period for audit logs under the enterprise plan?', 'resolved', 'medium',
     'Enterprise plan retains audit logs for 7 years. Documentation link was shared.'),
    ('tb000000-0000-0000-0000-000000000007', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000002',
     'Performance degradation in EU region', 'Latency has increased by 3x for our EU-based users since the last deployment.', 'open', 'critical', NULL),
    ('tb000000-0000-0000-0000-000000000008', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000003',
     'Two-factor authentication setup', 'Need help enabling 2FA for all team members.', 'closed', 'medium',
     '2FA enabled for all team members using TOTP. Recovery codes were generated.'),
    ('tb000000-0000-0000-0000-000000000009', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000004',
     'Custom domain SSL certificate', 'Our custom domain SSL certificate is expiring next week and needs renewal.', 'in_progress', 'high', NULL),
    ('tb000000-0000-0000-0000-000000000010', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000005',
     'Audit log export request', 'We need to export all audit logs from the past 6 months for compliance review.', 'resolved', 'medium',
     'Audit log export completed and delivered via secure download link.');

-- -----------------------------------------------------------------------------
-- Knowledge Articles - TenantA (Acme Corp)
-- -----------------------------------------------------------------------------
INSERT INTO knowledge_articles (id, tenant_id, title, content, category, tags) VALUES
    ('ka000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001',
     'Getting Started with Acme Dashboard',
     'Welcome to Acme Corp! This guide walks you through your first login, setting up your profile, and navigating the dashboard. Start by visiting https://dashboard.acmecorp.example.com and entering your credentials.',
     'onboarding', ARRAY['getting-started', 'dashboard', 'setup']),
    ('ka000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001',
     'How to Reset Your Password',
     'If you have forgotten your password, click the "Forgot Password" link on the login page. Enter your registered email and follow the instructions in the reset email. If you do not receive the email within 5 minutes, check your spam folder.',
     'account', ARRAY['password', 'reset', 'login']),
    ('ka000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001',
     'API Rate Limits and Quotas',
     'Acme Corp APIs enforce rate limits to ensure fair usage. Free plan: 100 req/min, Starter: 500 req/min, Business: 2000 req/min. If you exceed your limit, you will receive a 429 Too Many Requests response.',
     'api', ARRAY['rate-limit', 'api', 'quota']),
    ('ka000000-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000001',
     'Setting Up Slack Integration',
     'To connect Acme with Slack, navigate to Settings > Integrations > Slack. Click "Connect" and authorize the application in your Slack workspace. Notifications will be sent to the selected channel.',
     'integrations', ARRAY['slack', 'integration', 'notifications']),
    ('ka000000-0000-0000-0000-000000000005', 'a0000000-0000-0000-0000-000000000001',
     'Exporting Data and Reports',
     'You can export your data in CSV or JSON format from the Reports section. Select the date range and click "Export". For large datasets (over 10,000 rows), the export runs asynchronously and you will receive a download link via email.',
     'reports', ARRAY['export', 'csv', 'reports', 'data']);

-- -----------------------------------------------------------------------------
-- Knowledge Articles - TenantB (GlobalTech)
-- -----------------------------------------------------------------------------
INSERT INTO knowledge_articles (id, tenant_id, title, content, category, tags) VALUES
    ('kb000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001',
     'GlobalTech Platform Overview',
     'GlobalTech provides enterprise-grade SaaS solutions for global teams. This article covers the platform architecture, available modules, and how to get started with your enterprise deployment.',
     'onboarding', ARRAY['overview', 'platform', 'enterprise']),
    ('kb000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000001',
     'Configuring SAML SSO',
     'GlobalTech supports SAML 2.0 SSO with major identity providers (Okta, Azure AD, OneLogin). Navigate to Admin > Security > SSO to configure. You will need the IdP metadata URL and entity ID.',
     'security', ARRAY['sso', 'saml', 'okta', 'authentication']),
    ('kb000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000001',
     'Bulk User Import Guide',
     'To import users in bulk, prepare a CSV file with columns: name, email, role, department. Navigate to Admin > Users > Import. The system supports up to 10,000 users per import batch.',
     'admin', ARRAY['import', 'users', 'bulk', 'csv']),
    ('kb000000-0000-0000-0000-000000000004', 'b0000000-0000-0000-0000-000000000001',
     'Custom Domain and SSL Setup',
     'Enterprise plan users can configure a custom domain. Go to Settings > Domain. Add your CNAME record pointing to platform.globaltech.example.com. SSL certificates are automatically provisioned via Let''s Encrypt.',
     'infrastructure', ARRAY['custom-domain', 'ssl', 'dns', 'enterprise']),
    ('kb000000-0000-0000-0000-000000000005', 'b0000000-0000-0000-0000-000000000001',
     'Audit Logging and Compliance',
     'GlobalTech maintains comprehensive audit logs for all user actions. Enterprise plan retains logs for 7 years. Logs can be exported via the Admin > Compliance > Audit Logs section or through the Audit API endpoint.',
     'compliance', ARRAY['audit', 'logging', 'compliance', 'enterprise']);

-- -----------------------------------------------------------------------------
-- Billing Records - TenantA (Acme Corp) - 10 records
-- -----------------------------------------------------------------------------
INSERT INTO billing_records (id, tenant_id, customer_id, amount, type, status, description) VALUES
    ('ra000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000001',
     29.99, 'charge', 'completed', 'Monthly subscription - Starter plan'),
    ('ra000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000002',
     99.99, 'charge', 'completed', 'Monthly subscription - Business plan'),
    ('ra000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000003',
     0.00, 'charge', 'completed', 'Monthly subscription - Free plan'),
    ('ra000000-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000004',
     29.99, 'charge', 'completed', 'Monthly subscription - Starter plan'),
    ('ra000000-0000-0000-0000-000000000005', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000005',
     99.99, 'charge', 'completed', 'Monthly subscription - Business plan'),
    ('ra000000-0000-0000-0000-000000000006', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000001',
     15.00, 'refund', 'completed', 'Partial refund for service outage'),
    ('ra000000-0000-0000-0000-000000000007', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000002',
     50.00, 'credit', 'completed', 'Loyalty credit applied'),
    ('ra000000-0000-0000-0000-000000000008', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000004',
     10.00, 'adjustment', 'completed', 'Proration adjustment for mid-cycle upgrade'),
    ('ra000000-0000-0000-0000-000000000009', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000005',
     99.99, 'charge', 'pending', 'Monthly subscription renewal - Business plan'),
    ('ra000000-0000-0000-0000-000000000010', 'a0000000-0000-0000-0000-000000000001', 'ca000000-0000-0000-0000-000000000001',
     29.99, 'charge', 'failed', 'Monthly subscription renewal - payment method declined');

-- -----------------------------------------------------------------------------
-- Billing Records - TenantB (GlobalTech) - 10 records
-- -----------------------------------------------------------------------------
INSERT INTO billing_records (id, tenant_id, customer_id, amount, type, status, description) VALUES
    ('rb000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000001',
     199.99, 'charge', 'completed', 'Monthly subscription - Business plan'),
    ('rb000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000002',
     499.99, 'charge', 'completed', 'Monthly subscription - Enterprise plan'),
    ('rb000000-0000-0000-0000-000000000003', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000003',
     49.99, 'charge', 'completed', 'Monthly subscription - Starter plan'),
    ('rb000000-0000-0000-0000-000000000004', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000004',
     499.99, 'charge', 'completed', 'Monthly subscription - Enterprise plan'),
    ('rb000000-0000-0000-0000-000000000005', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000005',
     199.99, 'charge', 'completed', 'Monthly subscription - Business plan'),
    ('rb000000-0000-0000-0000-000000000006', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000002',
     250.00, 'refund', 'completed', 'Refund for duplicate charge'),
    ('rb000000-0000-0000-0000-000000000007', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000004',
     500.00, 'credit', 'completed', 'Annual loyalty credit - Enterprise plan'),
    ('rb000000-0000-0000-0000-000000000008', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000003',
     25.00, 'adjustment', 'completed', 'Proration for mid-cycle plan change'),
    ('rb000000-0000-0000-0000-000000000009', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000001',
     199.99, 'charge', 'pending', 'Monthly subscription renewal - Business plan'),
    ('rb000000-0000-0000-0000-000000000010', 'b0000000-0000-0000-0000-000000000001', 'cb000000-0000-0000-0000-000000000005',
     199.99, 'charge', 'failed', 'Monthly subscription renewal - payment method expired');
