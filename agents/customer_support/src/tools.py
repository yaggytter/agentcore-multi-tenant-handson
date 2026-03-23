"""
Custom tool definitions for the Customer Support Agent.
These tools handle tenant-specific operations that are local to the agent.
"""

import json
import logging
from typing import Any

from strands import tool

logger = logging.getLogger(__name__)

# Simulated in-memory data store for demo purposes.
# In production, these would call external APIs or databases.
CUSTOMER_DB = {
    "tenant-a": {
        "cust-001": {
            "customer_id": "cust-001",
            "name": "田中太郎",
            "email": "tanaka@acme-corp.example.com",
            "plan": "enterprise",
            "status": "active",
            "company": "Acme Corp",
            "created_at": "2024-01-15",
        },
        "cust-002": {
            "customer_id": "cust-002",
            "name": "佐藤花子",
            "email": "sato@acme-corp.example.com",
            "plan": "enterprise",
            "status": "active",
            "company": "Acme Corp",
            "created_at": "2024-03-01",
        },
    },
    "tenant-b": {
        "cust-101": {
            "customer_id": "cust-101",
            "name": "John Smith",
            "email": "john@globaltech.example.com",
            "plan": "professional",
            "status": "active",
            "company": "GlobalTech",
            "created_at": "2024-02-20",
        },
        "cust-102": {
            "customer_id": "cust-102",
            "name": "Jane Doe",
            "email": "jane@globaltech.example.com",
            "plan": "professional",
            "status": "suspended",
            "company": "GlobalTech",
            "created_at": "2024-04-10",
        },
    },
}

FAQ_DB = {
    "tenant-a": [
        {
            "id": "faq-a-001",
            "question": "パスワードをリセットするにはどうすればよいですか？",
            "question_en": "How do I reset my password?",
            "answer": "設定画面の「セキュリティ」タブから「パスワードリセット」をクリックしてください。登録済みメールアドレスにリセットリンクが送信されます。",
            "answer_en": "Go to Settings > Security tab and click 'Reset Password'. A reset link will be sent to your registered email.",
            "category": "account",
        },
        {
            "id": "faq-a-002",
            "question": "請求書はどこで確認できますか？",
            "question_en": "Where can I view my invoices?",
            "answer": "管理画面の「請求・支払い」セクションから過去の請求書をダウンロードできます。",
            "answer_en": "You can download past invoices from the 'Billing & Payments' section in the admin dashboard.",
            "category": "billing",
        },
        {
            "id": "faq-a-003",
            "question": "APIレート制限について教えてください。",
            "question_en": "What are the API rate limits?",
            "answer": "Enterpriseプランでは1分あたり10,000リクエストまで利用可能です。制限に達した場合は429エラーが返されます。",
            "answer_en": "Enterprise plan allows up to 10,000 requests per minute. A 429 error is returned when the limit is reached.",
            "category": "technical",
        },
    ],
    "tenant-b": [
        {
            "id": "faq-b-001",
            "question": "How do I reset my password?",
            "answer": "Navigate to Account Settings > Security and click 'Change Password'. Follow the prompts to set a new password.",
            "category": "account",
        },
        {
            "id": "faq-b-002",
            "question": "How do I upgrade my plan?",
            "answer": "Go to Settings > Subscription and select your desired plan. Changes take effect at the next billing cycle.",
            "category": "billing",
        },
        {
            "id": "faq-b-003",
            "question": "What integrations are supported?",
            "answer": "We support Slack, Jira, GitHub, and Salesforce integrations. Visit Settings > Integrations to configure.",
            "category": "technical",
        },
    ],
}

ESCALATION_QUEUE: list[dict[str, Any]] = []


@tool
def get_customer_info(tenant_id: str, customer_id: str = "", email: str = "") -> str:
    """Look up customer information by tenant. Provide either customer_id or email.

    Args:
        tenant_id: The tenant identifier for data isolation.
        customer_id: The customer ID to look up (optional if email is provided).
        email: The customer email to look up (optional if customer_id is provided).

    Returns:
        JSON string with customer details or error message.
    """
    logger.info(
        f"Looking up customer for tenant={tenant_id}, "
        f"customer_id={customer_id}, email={email}"
    )

    tenant_customers = CUSTOMER_DB.get(tenant_id, {})

    if not tenant_customers:
        return json.dumps({
            "error": "Tenant not found or no customers registered.",
            "error_ja": "テナントが見つからないか、顧客が登録されていません。",
        })

    # Search by customer_id
    if customer_id and customer_id in tenant_customers:
        return json.dumps(tenant_customers[customer_id], ensure_ascii=False)

    # Search by email
    if email:
        for cust in tenant_customers.values():
            if cust["email"].lower() == email.lower():
                return json.dumps(cust, ensure_ascii=False)

    # List all customers if no specific filter
    if not customer_id and not email:
        customers = list(tenant_customers.values())
        return json.dumps({
            "total": len(customers),
            "customers": customers,
        }, ensure_ascii=False)

    return json.dumps({
        "error": "Customer not found.",
        "error_ja": "顧客が見つかりません。",
    })


@tool
def escalate_ticket(
    tenant_id: str,
    ticket_id: str,
    reason: str,
    priority: str = "high",
    assigned_team: str = "tier2-support",
) -> str:
    """Escalate a support ticket to a human agent or specialized team.

    Args:
        tenant_id: The tenant identifier for data isolation.
        ticket_id: The ticket ID to escalate.
        reason: The reason for escalation.
        priority: Escalation priority - one of 'medium', 'high', 'critical'. Defaults to 'high'.
        assigned_team: The team to assign the escalation to. Defaults to 'tier2-support'.

    Returns:
        JSON string confirming the escalation or error message.
    """
    logger.info(
        f"Escalating ticket {ticket_id} for tenant={tenant_id}, "
        f"priority={priority}, team={assigned_team}"
    )

    valid_priorities = {"medium", "high", "critical"}
    if priority not in valid_priorities:
        return json.dumps({
            "error": f"Invalid priority. Must be one of: {', '.join(valid_priorities)}",
        })

    valid_teams = {"tier2-support", "engineering", "billing-ops", "management"}
    if assigned_team not in valid_teams:
        return json.dumps({
            "error": f"Invalid team. Must be one of: {', '.join(valid_teams)}",
        })

    escalation = {
        "escalation_id": f"esc-{len(ESCALATION_QUEUE) + 1:04d}",
        "tenant_id": tenant_id,
        "ticket_id": ticket_id,
        "reason": reason,
        "priority": priority,
        "assigned_team": assigned_team,
        "status": "pending",
    }
    ESCALATION_QUEUE.append(escalation)

    logger.info(f"Escalation created: {escalation['escalation_id']}")

    return json.dumps({
        "success": True,
        "escalation": escalation,
        "message": f"Ticket {ticket_id} has been escalated to {assigned_team}.",
        "message_ja": f"チケット {ticket_id} が {assigned_team} にエスカレーションされました。",
    }, ensure_ascii=False)


@tool
def get_faq(tenant_id: str, category: str = "", query: str = "") -> str:
    """Retrieve FAQ answers for the tenant. Optionally filter by category or search query.

    Args:
        tenant_id: The tenant identifier for data isolation.
        category: Filter by FAQ category (e.g., 'account', 'billing', 'technical'). Optional.
        query: Search term to match against questions. Optional.

    Returns:
        JSON string with matching FAQ entries.
    """
    logger.info(
        f"Retrieving FAQ for tenant={tenant_id}, "
        f"category={category}, query={query}"
    )

    tenant_faqs = FAQ_DB.get(tenant_id, [])

    if not tenant_faqs:
        return json.dumps({
            "error": "No FAQ entries found for this tenant.",
            "error_ja": "このテナントのFAQエントリが見つかりません。",
        })

    results = tenant_faqs

    # Filter by category
    if category:
        results = [faq for faq in results if faq.get("category") == category]

    # Filter by search query (simple substring match)
    if query:
        query_lower = query.lower()
        results = [
            faq
            for faq in results
            if query_lower in faq.get("question", "").lower()
            or query_lower in faq.get("question_en", "").lower()
            or query_lower in faq.get("answer", "").lower()
            or query_lower in faq.get("answer_en", "").lower()
        ]

    return json.dumps({
        "total": len(results),
        "faqs": results,
    }, ensure_ascii=False)
