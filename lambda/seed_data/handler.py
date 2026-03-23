"""
Seed Data Lambda
Creates test tenants, customers, support tickets, knowledge articles,
and billing data for the multi-tenant hands-on tutorial.

Tenants:
  - TenantA (tenant-a): Acme Corp - Enterprise plan (Japanese)
  - TenantB (tenant-b): GlobalTech - Professional plan (English)
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import psycopg2
from psycopg2.extras import execute_values

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "support")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

NOW = datetime.now(timezone.utc)


def get_connection():
    """Create a database connection."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=10,
    )
    conn.autocommit = False
    return conn


# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

TENANTS = [
    {
        "tenant_id": "tenant-a",
        "name": "Acme Corp",
        "plan": "enterprise",
        "status": "active",
        "domain": "acme-corp.example.com",
        "locale": "ja",
    },
    {
        "tenant_id": "tenant-b",
        "name": "GlobalTech",
        "plan": "professional",
        "status": "active",
        "domain": "globaltech.example.com",
        "locale": "en",
    },
]

CUSTOMERS = [
    # Tenant A customers
    {
        "customer_id": "cust-001",
        "tenant_id": "tenant-a",
        "name": "田中太郎",
        "email": "tanaka@acme-corp.example.com",
        "plan": "enterprise",
        "status": "active",
    },
    {
        "customer_id": "cust-002",
        "tenant_id": "tenant-a",
        "name": "佐藤花子",
        "email": "sato@acme-corp.example.com",
        "plan": "enterprise",
        "status": "active",
    },
    {
        "customer_id": "cust-003",
        "tenant_id": "tenant-a",
        "name": "鈴木一郎",
        "email": "suzuki@acme-corp.example.com",
        "plan": "enterprise",
        "status": "active",
    },
    # Tenant B customers
    {
        "customer_id": "cust-101",
        "tenant_id": "tenant-b",
        "name": "John Smith",
        "email": "john@globaltech.example.com",
        "plan": "professional",
        "status": "active",
    },
    {
        "customer_id": "cust-102",
        "tenant_id": "tenant-b",
        "name": "Jane Doe",
        "email": "jane@globaltech.example.com",
        "plan": "professional",
        "status": "suspended",
    },
    {
        "customer_id": "cust-103",
        "tenant_id": "tenant-b",
        "name": "Bob Wilson",
        "email": "bob@globaltech.example.com",
        "plan": "professional",
        "status": "active",
    },
]

SUPPORT_TICKETS = [
    # Tenant A tickets (Japanese)
    {
        "ticket_id": "TKT-A001",
        "tenant_id": "tenant-a",
        "customer_id": "cust-001",
        "subject": "ログインできません",
        "description": "パスワードを変更した後、ログインができなくなりました。リセットメールも届きません。",
        "status": "open",
        "priority": "high",
        "category": "account",
    },
    {
        "ticket_id": "TKT-A002",
        "tenant_id": "tenant-a",
        "customer_id": "cust-002",
        "subject": "請求金額が間違っています",
        "description": "今月の請求書の金額が先月と異なっています。プラン変更はしていません。",
        "status": "in_progress",
        "priority": "high",
        "category": "billing",
    },
    {
        "ticket_id": "TKT-A003",
        "tenant_id": "tenant-a",
        "customer_id": "cust-001",
        "subject": "APIレスポンスが遅い",
        "description": "昨日からAPIのレスポンス時間が3秒以上かかるようになりました。",
        "status": "open",
        "priority": "critical",
        "category": "technical",
    },
    {
        "ticket_id": "TKT-A004",
        "tenant_id": "tenant-a",
        "customer_id": "cust-003",
        "subject": "新機能のリクエスト: Slack連携",
        "description": "チケット通知をSlackに送信する機能を追加してほしいです。",
        "status": "open",
        "priority": "low",
        "category": "feature_request",
    },
    {
        "ticket_id": "TKT-A005",
        "tenant_id": "tenant-a",
        "customer_id": "cust-002",
        "subject": "データエクスポートのエラー",
        "description": "CSVエクスポートを実行すると500エラーが返されます。",
        "status": "resolved",
        "priority": "medium",
        "category": "technical",
        "resolution": "エクスポートモジュールのバグを修正しました。",
    },
    # Tenant B tickets (English)
    {
        "ticket_id": "TKT-B001",
        "tenant_id": "tenant-b",
        "customer_id": "cust-101",
        "subject": "Cannot access dashboard",
        "description": "Getting a 403 error when trying to access the analytics dashboard.",
        "status": "open",
        "priority": "high",
        "category": "technical",
    },
    {
        "ticket_id": "TKT-B002",
        "tenant_id": "tenant-b",
        "customer_id": "cust-102",
        "subject": "Account suspended without notice",
        "description": "My account was suspended but I haven't received any notification. Please clarify.",
        "status": "in_progress",
        "priority": "high",
        "category": "account",
    },
    {
        "ticket_id": "TKT-B003",
        "tenant_id": "tenant-b",
        "customer_id": "cust-101",
        "subject": "Request for invoice copy",
        "description": "I need a copy of the invoice for Q4 2025 for accounting purposes.",
        "status": "resolved",
        "priority": "low",
        "category": "billing",
        "resolution": "Invoice copy sent to customer email.",
    },
    {
        "ticket_id": "TKT-B004",
        "tenant_id": "tenant-b",
        "customer_id": "cust-103",
        "subject": "Integration with GitHub not working",
        "description": "The GitHub webhook integration stopped working after the latest update.",
        "status": "open",
        "priority": "medium",
        "category": "technical",
    },
]

KNOWLEDGE_ARTICLES = [
    # Tenant A articles (Japanese)
    {
        "article_id": "KB-A001",
        "tenant_id": "tenant-a",
        "title": "パスワードリセット手順",
        "content": (
            "1. ログイン画面で「パスワードを忘れた場合」をクリック\n"
            "2. 登録済みメールアドレスを入力\n"
            "3. 受信したメールのリンクをクリック\n"
            "4. 新しいパスワードを設定\n\n"
            "メールが届かない場合は、迷惑メールフォルダをご確認ください。"
        ),
        "category": "account",
        "tags": ["パスワード", "ログイン", "アカウント"],
    },
    {
        "article_id": "KB-A002",
        "tenant_id": "tenant-a",
        "title": "請求書の確認方法",
        "content": (
            "1. 管理画面にログイン\n"
            "2. 左メニューの「請求・支払い」をクリック\n"
            "3. 「請求履歴」タブを選択\n"
            "4. 該当月の請求書の「ダウンロード」をクリック\n\n"
            "PDFとCSV形式でダウンロード可能です。"
        ),
        "category": "billing",
        "tags": ["請求書", "支払い", "経理"],
    },
    {
        "article_id": "KB-A003",
        "tenant_id": "tenant-a",
        "title": "API利用ガイド",
        "content": (
            "## 認証\n"
            "APIキーをヘッダーに含めてリクエストしてください。\n"
            "X-API-Key: your-api-key\n\n"
            "## レート制限\n"
            "- Enterpriseプラン: 10,000リクエスト/分\n"
            "- 制限超過時: HTTP 429を返却\n\n"
            "## エンドポイント\n"
            "ベースURL: https://api.acme-corp.example.com/v1"
        ),
        "category": "technical",
        "tags": ["API", "認証", "レート制限"],
    },
    # Tenant B articles (English)
    {
        "article_id": "KB-B001",
        "tenant_id": "tenant-b",
        "title": "Getting Started with the Dashboard",
        "content": (
            "1. Log in to your account at dashboard.globaltech.example.com\n"
            "2. Navigate to the Analytics section\n"
            "3. Select your date range and metrics\n"
            "4. Use filters to drill down into specific data\n\n"
            "For permission issues, contact your admin to verify your role."
        ),
        "category": "technical",
        "tags": ["dashboard", "analytics", "getting started"],
    },
    {
        "article_id": "KB-B002",
        "tenant_id": "tenant-b",
        "title": "Billing and Subscription FAQ",
        "content": (
            "## Plans\n"
            "- Starter: $29/month\n"
            "- Professional: $99/month\n"
            "- Enterprise: Custom pricing\n\n"
            "## Upgrading\n"
            "Go to Settings > Subscription to change your plan.\n"
            "Upgrades take effect immediately. Downgrades at next billing cycle.\n\n"
            "## Invoices\n"
            "Invoices are generated on the 1st of each month and sent via email."
        ),
        "category": "billing",
        "tags": ["billing", "subscription", "plans", "invoices"],
    },
    {
        "article_id": "KB-B003",
        "tenant_id": "tenant-b",
        "title": "Integrations Setup Guide",
        "content": (
            "## Supported Integrations\n"
            "- Slack: Real-time notifications\n"
            "- GitHub: Issue and PR tracking\n"
            "- Jira: Two-way sync\n"
            "- Salesforce: Contact and deal sync\n\n"
            "## Setup\n"
            "1. Go to Settings > Integrations\n"
            "2. Click 'Connect' on your desired integration\n"
            "3. Authorize the connection\n"
            "4. Configure notification preferences"
        ),
        "category": "technical",
        "tags": ["integrations", "slack", "github", "jira"],
    },
]

BILLING_INFO = [
    # Tenant A billing
    {
        "billing_id": "BILL-A001",
        "tenant_id": "tenant-a",
        "customer_id": "cust-001",
        "plan_name": "Enterprise",
        "billing_cycle": "monthly",
        "amount": Decimal("50000"),
        "currency": "JPY",
        "payment_method": "credit_card",
        "status": "active",
    },
    {
        "billing_id": "BILL-A002",
        "tenant_id": "tenant-a",
        "customer_id": "cust-002",
        "plan_name": "Enterprise",
        "billing_cycle": "monthly",
        "amount": Decimal("50000"),
        "currency": "JPY",
        "payment_method": "bank_transfer",
        "status": "active",
    },
    # Tenant B billing
    {
        "billing_id": "BILL-B001",
        "tenant_id": "tenant-b",
        "customer_id": "cust-101",
        "plan_name": "Professional",
        "billing_cycle": "monthly",
        "amount": Decimal("99.00"),
        "currency": "USD",
        "payment_method": "credit_card",
        "status": "active",
    },
    {
        "billing_id": "BILL-B002",
        "tenant_id": "tenant-b",
        "customer_id": "cust-103",
        "plan_name": "Professional",
        "billing_cycle": "annual",
        "amount": Decimal("990.00"),
        "currency": "USD",
        "payment_method": "credit_card",
        "status": "active",
    },
]


def generate_invoices() -> list[dict]:
    """Generate sample invoice history for the last 6 months."""
    invoices = []
    for month_offset in range(6):
        invoice_date = NOW - timedelta(days=30 * month_offset)
        due_date = invoice_date + timedelta(days=30)
        paid = month_offset > 0  # Current month not yet paid

        # Tenant A invoices
        invoices.append({
            "invoice_id": f"INV-A-{202600 - month_offset:06d}",
            "tenant_id": "tenant-a",
            "customer_id": "cust-001",
            "amount": Decimal("50000"),
            "currency": "JPY",
            "invoice_date": invoice_date,
            "due_date": due_date,
            "paid_date": invoice_date + timedelta(days=5) if paid else None,
            "status": "paid" if paid else "pending",
            "description": f"Enterprise Plan - {invoice_date.strftime('%Y年%m月')}",
        })

        # Tenant B invoices
        invoices.append({
            "invoice_id": f"INV-B-{202600 - month_offset:06d}",
            "tenant_id": "tenant-b",
            "customer_id": "cust-101",
            "amount": Decimal("99.00"),
            "currency": "USD",
            "invoice_date": invoice_date,
            "due_date": due_date,
            "paid_date": invoice_date + timedelta(days=3) if paid else None,
            "status": "paid" if paid else "pending",
            "description": f"Professional Plan - {invoice_date.strftime('%B %Y')}",
        })

    return invoices


# ---------------------------------------------------------------------------
# Database seeding functions
# ---------------------------------------------------------------------------

def seed_tenants(cursor):
    """Insert tenant records."""
    logger.info("Seeding tenants...")
    for t in TENANTS:
        cursor.execute(
            """
            INSERT INTO tenants (tenant_id, name, plan, status, domain, locale, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tenant_id) DO UPDATE SET
                name = EXCLUDED.name,
                plan = EXCLUDED.plan,
                status = EXCLUDED.status
            """,
            (t["tenant_id"], t["name"], t["plan"], t["status"],
             t["domain"], t["locale"], NOW),
        )
    logger.info(f"Seeded {len(TENANTS)} tenants.")


def seed_customers(cursor):
    """Insert customer records."""
    logger.info("Seeding customers...")
    for c in CUSTOMERS:
        cursor.execute(
            """
            INSERT INTO customers
                (customer_id, tenant_id, name, email, plan, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (customer_id, tenant_id) DO UPDATE SET
                name = EXCLUDED.name,
                email = EXCLUDED.email,
                status = EXCLUDED.status
            """,
            (c["customer_id"], c["tenant_id"], c["name"],
             c["email"], c["plan"], c["status"], NOW),
        )
    logger.info(f"Seeded {len(CUSTOMERS)} customers.")


def seed_tickets(cursor):
    """Insert support ticket records."""
    logger.info("Seeding support tickets...")
    for i, t in enumerate(SUPPORT_TICKETS):
        created_at = NOW - timedelta(days=len(SUPPORT_TICKETS) - i)
        resolved_at = None
        if t["status"] == "resolved":
            resolved_at = created_at + timedelta(hours=4)

        cursor.execute(
            """
            INSERT INTO support_tickets
                (ticket_id, tenant_id, customer_id, subject, description,
                 status, priority, category, resolution, created_at,
                 updated_at, resolved_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticket_id) DO UPDATE SET
                status = EXCLUDED.status,
                resolution = EXCLUDED.resolution
            """,
            (t["ticket_id"], t["tenant_id"], t["customer_id"],
             t["subject"], t["description"], t["status"], t["priority"],
             t["category"], t.get("resolution"), created_at, created_at,
             resolved_at),
        )
    logger.info(f"Seeded {len(SUPPORT_TICKETS)} support tickets.")


def seed_knowledge_articles(cursor):
    """Insert knowledge base articles."""
    logger.info("Seeding knowledge articles...")
    for a in KNOWLEDGE_ARTICLES:
        cursor.execute(
            """
            INSERT INTO knowledge_articles
                (article_id, tenant_id, title, content, category, tags,
                 author, created_at, updated_at, view_count)
            VALUES (%s, %s, %s, %s, %s, %s, 'system', %s, %s, 0)
            ON CONFLICT (article_id) DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content
            """,
            (a["article_id"], a["tenant_id"], a["title"],
             a["content"], a["category"],
             json.dumps(a["tags"], ensure_ascii=False),
             NOW, NOW),
        )
    logger.info(f"Seeded {len(KNOWLEDGE_ARTICLES)} knowledge articles.")


def seed_billing(cursor):
    """Insert billing information."""
    logger.info("Seeding billing info...")
    for b in BILLING_INFO:
        next_billing = NOW + timedelta(days=30)
        cursor.execute(
            """
            INSERT INTO billing_info
                (billing_id, tenant_id, customer_id, plan_name,
                 billing_cycle, amount, currency, next_billing_date,
                 payment_method, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (billing_id) DO UPDATE SET
                amount = EXCLUDED.amount,
                status = EXCLUDED.status
            """,
            (b["billing_id"], b["tenant_id"], b["customer_id"],
             b["plan_name"], b["billing_cycle"], b["amount"],
             b["currency"], next_billing, b["payment_method"],
             b["status"], NOW),
        )
    logger.info(f"Seeded {len(BILLING_INFO)} billing records.")


def seed_invoices(cursor):
    """Insert invoice history."""
    invoices = generate_invoices()
    logger.info("Seeding invoices...")
    for inv in invoices:
        cursor.execute(
            """
            INSERT INTO invoices
                (invoice_id, tenant_id, customer_id, amount, currency,
                 invoice_date, due_date, paid_date, status, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (invoice_id) DO UPDATE SET
                status = EXCLUDED.status,
                paid_date = EXCLUDED.paid_date
            """,
            (inv["invoice_id"], inv["tenant_id"], inv["customer_id"],
             inv["amount"], inv["currency"], inv["invoice_date"],
             inv["due_date"], inv["paid_date"], inv["status"],
             inv["description"]),
        )
    logger.info(f"Seeded {len(invoices)} invoices.")


def seed_tenant_user_mappings(cursor):
    """Insert DynamoDB-style user-to-tenant mappings into a local table for reference."""
    logger.info("Seeding tenant user mappings...")
    mappings = [
        ("user-a-001", "tenant-a", "Acme Corp", "enterprise", "admin"),
        ("user-a-002", "tenant-a", "Acme Corp", "enterprise", "user"),
        ("user-b-001", "tenant-b", "GlobalTech", "professional", "admin"),
        ("user-b-002", "tenant-b", "GlobalTech", "professional", "user"),
    ]
    for user_id, tenant_id, tenant_name, plan, role in mappings:
        cursor.execute(
            """
            INSERT INTO tenant_user_mappings
                (user_id, tenant_id, tenant_name, tenant_plan, role, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                role = EXCLUDED.role
            """,
            (user_id, tenant_id, tenant_name, plan, role, NOW),
        )
    logger.info(f"Seeded {len(mappings)} user-tenant mappings.")


def lambda_handler(event, context):
    """
    AWS Lambda handler for seeding demo data.
    Idempotent -- safe to run multiple times (uses ON CONFLICT).
    """
    logger.info(f"Seed data Lambda invoked: {json.dumps(event)}")

    action = event.get("action", "seed_all")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if action == "seed_all":
                seed_tenants(cur)
                seed_customers(cur)
                seed_tickets(cur)
                seed_knowledge_articles(cur)
                seed_billing(cur)
                seed_invoices(cur)
                seed_tenant_user_mappings(cur)
            elif action == "seed_tenants":
                seed_tenants(cur)
            elif action == "seed_customers":
                seed_customers(cur)
            elif action == "seed_tickets":
                seed_tickets(cur)
            elif action == "seed_knowledge":
                seed_knowledge_articles(cur)
            elif action == "seed_billing":
                seed_billing(cur)
                seed_invoices(cur)
            elif action == "clean_all":
                logger.info("Cleaning all seed data...")
                cur.execute("DELETE FROM invoices")
                cur.execute("DELETE FROM refunds")
                cur.execute("DELETE FROM billing_info")
                cur.execute("DELETE FROM knowledge_articles")
                cur.execute("DELETE FROM support_tickets")
                cur.execute("DELETE FROM customers")
                cur.execute("DELETE FROM tenant_user_mappings")
                cur.execute("DELETE FROM tenants")
                logger.info("All seed data cleaned.")
            else:
                conn.rollback()
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": f"Unknown action: {action}. "
                        "Valid: seed_all, seed_tenants, seed_customers, "
                        "seed_tickets, seed_knowledge, seed_billing, clean_all",
                    }),
                }

            conn.commit()

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Seed data action '{action}' completed successfully.",
                "tenants": [t["tenant_id"] for t in TENANTS],
            }),
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Seed data failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Seed data failed: {str(e)}"}),
        }
    finally:
        conn.close()
