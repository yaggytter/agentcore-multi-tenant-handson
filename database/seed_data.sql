-- =============================================================================
-- Seed Data for AgentCore Multi-Tenant Customer Support
-- =============================================================================
-- Populates the database with test data for two tenants:
--   - tenant-a: Acme Corp (enterprise plan)
--   - tenant-b: GlobalTech (professional plan)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tenants
-- -----------------------------------------------------------------------------
INSERT INTO tenants (tenant_id, name, plan, status, domain, locale) VALUES
    ('tenant-a', 'Acme Corp', 'enterprise', 'active', 'acmecorp.example.com', 'ja'),
    ('tenant-b', 'GlobalTech', 'professional', 'active', 'globaltech.example.com', 'en');

-- -----------------------------------------------------------------------------
-- Customers - tenant-a (Acme Corp)
-- -----------------------------------------------------------------------------
INSERT INTO customers (id, tenant_id, name, email, phone, plan, status) VALUES
    ('ca000000-0000-0000-0000-000000000001', 'tenant-a', '田中太郎', 'tanaka@acme-corp.example.com', '090-1234-5678', 'enterprise', 'active'),
    ('ca000000-0000-0000-0000-000000000002', 'tenant-a', '佐藤花子', 'sato@acme-corp.example.com', '090-2345-6789', 'enterprise', 'active'),
    ('ca000000-0000-0000-0000-000000000003', 'tenant-a', '鈴木一郎', 'suzuki@acme-corp.example.com', '090-3456-7890', 'enterprise', 'active'),
    ('ca000000-0000-0000-0000-000000000004', 'tenant-a', '高橋明美', 'takahashi@acme-corp.example.com', NULL, 'enterprise', 'active'),
    ('ca000000-0000-0000-0000-000000000005', 'tenant-a', '渡辺健太', 'watanabe@acme-corp.example.com', NULL, 'enterprise', 'suspended');

-- -----------------------------------------------------------------------------
-- Customers - tenant-b (GlobalTech)
-- -----------------------------------------------------------------------------
INSERT INTO customers (id, tenant_id, name, email, phone, plan, status) VALUES
    ('cb000000-0000-0000-0000-000000000001', 'tenant-b', 'John Smith', 'john@globaltech.example.com', '+1-555-0101', 'professional', 'active'),
    ('cb000000-0000-0000-0000-000000000002', 'tenant-b', 'Jane Doe', 'jane@globaltech.example.com', '+1-555-0102', 'professional', 'active'),
    ('cb000000-0000-0000-0000-000000000003', 'tenant-b', 'Bob Wilson', 'bob@globaltech.example.com', '+1-555-0103', 'professional', 'active'),
    ('cb000000-0000-0000-0000-000000000004', 'tenant-b', 'Alice Brown', 'alice@globaltech.example.com', NULL, 'professional', 'active'),
    ('cb000000-0000-0000-0000-000000000005', 'tenant-b', 'Charlie Davis', 'charlie@globaltech.example.com', NULL, 'professional', 'suspended');

-- -----------------------------------------------------------------------------
-- Support Tickets - tenant-a (Acme Corp)
-- -----------------------------------------------------------------------------
INSERT INTO support_tickets (tenant_id, customer_id, ticket_id, subject, description, status, priority, category, resolution) VALUES
    ('tenant-a', 'ca000000-0000-0000-0000-000000000001', 'TKT-A001', 'ダッシュボードにログインできません', '認証情報を入力後、403エラーが表示されます。', 'open', 'high', 'account', NULL),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000002', 'TKT-A002', '請求書の金額が不一致', '先月の請求書の金額が見積額と異なります。', 'in_progress', 'medium', 'billing', NULL),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000003', 'TKT-A003', 'ダークモード機能のリクエスト', 'アプリケーションにダークモードオプションが欲しいです。', 'open', 'low', 'general', NULL),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000004', 'TKT-A004', 'APIレート制限の問題', 'ピーク時にレート制限に達します。クォータの増加は可能ですか？', 'waiting_on_customer', 'high', 'technical', NULL),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000005', 'TKT-A005', 'データエクスポートが動作しない', 'CSVエクスポート機能で10,000行以上のレポートが空ファイルになります。', 'in_progress', 'critical', 'technical', NULL),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000001', 'TKT-A006', 'パスワードリセットメールが届かない', 'パスワードリセットを要求しましたがメールが届きません。', 'resolved', 'medium', 'account', 'スパムフィルターに捕捉されていました。ホワイトリスト登録の手順をご案内しました。'),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000002', 'TKT-A007', 'Slack連携の不具合', 'v2.3にアップデート後、Slack連携が動作しなくなりました。', 'open', 'high', 'technical', NULL),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000003', 'TKT-A008', 'アカウントアップグレードのリクエスト', 'Freeアカウントからstarterプランへのアップグレードを希望します。', 'closed', 'low', 'account', 'starterプランへのアップグレードが完了しました。'),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000004', 'TKT-A009', 'ページの読み込みが遅い', '先週からダッシュボードの読み込みに10秒以上かかります。', 'in_progress', 'high', 'technical', NULL),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000005', 'TKT-A010', 'Webhook配信の失敗', 'エンドポイントへのWebhookがタイムアウトエラーで失敗しています。', 'resolved', 'medium', 'technical', 'Webhookタイムアウトを30秒に増加し、リトライロジックを追加しました。');

-- -----------------------------------------------------------------------------
-- Support Tickets - tenant-b (GlobalTech)
-- -----------------------------------------------------------------------------
INSERT INTO support_tickets (tenant_id, customer_id, ticket_id, subject, description, status, priority, category, resolution) VALUES
    ('tenant-b', 'cb000000-0000-0000-0000-000000000001', 'TKT-B001', 'SSO configuration help', 'Need help configuring SAML SSO with Okta.', 'open', 'high', 'technical', NULL),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000002', 'TKT-B002', 'Custom report template', 'Can we create custom report templates for quarterly review?', 'in_progress', 'medium', 'general', NULL),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000003', 'TKT-B003', 'Mobile app crash on Android 14', 'App crashes immediately on Pixel 8 running Android 14.', 'open', 'critical', 'technical', NULL),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000004', 'TKT-B004', 'Bulk user import failing', 'Importing 5000+ users via CSV fails with generic error.', 'in_progress', 'high', 'technical', NULL),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000005', 'TKT-B005', 'API docs update request', 'v3 API docs missing new pagination parameters.', 'waiting_on_customer', 'low', 'general', NULL),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000001', 'TKT-B006', 'Data retention policy', 'What is the data retention period for audit logs?', 'resolved', 'medium', 'general', 'Enterprise plan retains logs for 7 years.'),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000002', 'TKT-B007', 'EU region performance', 'Latency increased 3x for EU users since last deployment.', 'open', 'critical', 'technical', NULL),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000003', 'TKT-B008', '2FA setup help', 'Need help enabling 2FA for all team members.', 'closed', 'medium', 'account', '2FA enabled for all members using TOTP.'),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000004', 'TKT-B009', 'SSL certificate renewal', 'Custom domain SSL certificate expiring next week.', 'in_progress', 'high', 'technical', NULL),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000005', 'TKT-B010', 'Audit log export', 'Need to export 6 months of audit logs for compliance.', 'resolved', 'medium', 'general', 'Export completed and delivered via secure download.');

-- -----------------------------------------------------------------------------
-- Knowledge Articles - tenant-a (Acme Corp)
-- -----------------------------------------------------------------------------
INSERT INTO knowledge_articles (tenant_id, article_id, title, content, category, tags, author) VALUES
    ('tenant-a', 'KB-A001', 'パスワードをリセットするにはどうすればよいですか？', '設定画面の「セキュリティ」タブから「パスワードリセット」をクリックしてください。登録済みメールアドレスにリセットリンクが送信されます。', 'account', ARRAY['password', 'reset', 'login'], '田中太郎'),
    ('tenant-a', 'KB-A002', '請求書はどこで確認できますか？', '管理画面の「請求・支払い」セクションから過去の請求書をダウンロードできます。', 'billing', ARRAY['invoice', 'billing', 'payment'], '佐藤花子'),
    ('tenant-a', 'KB-A003', 'APIレート制限について', 'Enterpriseプランでは1分あたり10,000リクエストまで利用可能です。制限に達した場合は429エラーが返されます。', 'technical', ARRAY['api', 'rate-limit', 'quota'], '鈴木一郎'),
    ('tenant-a', 'KB-A004', 'Slack連携の設定方法', '設定 > インテグレーション > Slack から連携を設定できます。「接続」をクリックしてSlackワークスペースで認証してください。', 'integrations', ARRAY['slack', 'integration'], '田中太郎'),
    ('tenant-a', 'KB-A005', 'データエクスポート機能の使い方', 'レポートセクションからCSVまたはJSON形式でデータをエクスポートできます。10,000行以上の場合は非同期で処理されます。', 'reports', ARRAY['export', 'csv', 'reports'], '佐藤花子');

-- -----------------------------------------------------------------------------
-- Knowledge Articles - tenant-b (GlobalTech)
-- -----------------------------------------------------------------------------
INSERT INTO knowledge_articles (tenant_id, article_id, title, content, category, tags, author) VALUES
    ('tenant-b', 'KB-B001', 'Getting Started with GlobalTech', 'Welcome to GlobalTech! This guide walks through your first login, profile setup, and dashboard navigation.', 'onboarding', ARRAY['getting-started', 'setup'], 'John Smith'),
    ('tenant-b', 'KB-B002', 'Configuring SAML SSO', 'GlobalTech supports SAML 2.0 SSO with Okta, Azure AD, and OneLogin. Navigate to Admin > Security > SSO to configure.', 'security', ARRAY['sso', 'saml', 'authentication'], 'Jane Doe'),
    ('tenant-b', 'KB-B003', 'Bulk User Import Guide', 'Prepare a CSV with columns: name, email, role, department. Go to Admin > Users > Import. Max 10,000 users per batch.', 'admin', ARRAY['import', 'users', 'csv'], 'Bob Wilson'),
    ('tenant-b', 'KB-B004', 'Custom Domain and SSL Setup', 'Enterprise users can configure custom domains. Add CNAME record pointing to platform.globaltech.example.com. SSL auto-provisioned.', 'infrastructure', ARRAY['domain', 'ssl', 'dns'], 'Alice Brown'),
    ('tenant-b', 'KB-B005', 'Audit Logging and Compliance', 'Comprehensive audit logs for all actions. Enterprise retains logs for 7 years. Export via Admin > Compliance > Audit Logs.', 'compliance', ARRAY['audit', 'logging', 'compliance'], 'Charlie Davis');

-- -----------------------------------------------------------------------------
-- Billing Records - tenant-a (Acme Corp)
-- -----------------------------------------------------------------------------
INSERT INTO billing_records (tenant_id, customer_id, amount, type, status, description) VALUES
    ('tenant-a', 'ca000000-0000-0000-0000-000000000001', 299.99, 'charge', 'completed', 'Monthly subscription - Enterprise plan'),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000002', 299.99, 'charge', 'completed', 'Monthly subscription - Enterprise plan'),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000003', 299.99, 'charge', 'completed', 'Monthly subscription - Enterprise plan'),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000001', 50.00, 'refund', 'completed', 'サービス障害に対する一部返金'),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000002', 100.00, 'credit', 'completed', 'ロイヤリティクレジット適用'),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000004', 299.99, 'charge', 'pending', 'Monthly subscription renewal'),
    ('tenant-a', 'ca000000-0000-0000-0000-000000000005', 299.99, 'charge', 'failed', 'Payment method declined');

-- -----------------------------------------------------------------------------
-- Billing Records - tenant-b (GlobalTech)
-- -----------------------------------------------------------------------------
INSERT INTO billing_records (tenant_id, customer_id, amount, type, status, description) VALUES
    ('tenant-b', 'cb000000-0000-0000-0000-000000000001', 199.99, 'charge', 'completed', 'Monthly subscription - Professional plan'),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000002', 199.99, 'charge', 'completed', 'Monthly subscription - Professional plan'),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000003', 199.99, 'charge', 'completed', 'Monthly subscription - Professional plan'),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000002', 100.00, 'refund', 'completed', 'Refund for duplicate charge'),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000004', 200.00, 'credit', 'completed', 'Annual loyalty credit'),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000001', 199.99, 'charge', 'pending', 'Monthly subscription renewal'),
    ('tenant-b', 'cb000000-0000-0000-0000-000000000005', 199.99, 'charge', 'failed', 'Payment method expired');
