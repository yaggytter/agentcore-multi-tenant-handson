"""
Gateway Tool Lambda: Billing Inquiry
Handles billing information retrieval, refund processing, and invoice history.
"""

import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "support")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

# Refund limits per tenant plan
REFUND_LIMITS = {
    "starter": Decimal("100.00"),
    "professional": Decimal("500.00"),
    "enterprise": Decimal("5000.00"),
}

DEFAULT_REFUND_LIMIT = Decimal("100.00")


def get_connection():
    """Create a database connection."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=5,
    )
    conn.autocommit = False
    return conn


def set_tenant_context(cursor, tenant_id: str):
    """Set the current tenant for Row Level Security."""
    cursor.execute(
        "SET app.current_tenant_id = %s",
        (tenant_id,),
    )


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def get_billing_info(tenant_id: str, customer_id: str) -> dict:
    """Get billing information for a customer."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            set_tenant_context(cur, tenant_id)

            cur.execute(
                """
                SELECT b.billing_id, b.customer_id, b.plan_name,
                       b.billing_cycle, b.amount, b.currency,
                       b.next_billing_date, b.payment_method,
                       b.status, b.created_at,
                       c.name AS customer_name, c.email AS customer_email
                FROM billing_info b
                JOIN customers c ON b.customer_id = c.customer_id
                    AND b.tenant_id = c.tenant_id
                WHERE b.customer_id = %s
                """,
                (customer_id,),
            )

            billing = cur.fetchone()
            conn.commit()

            if not billing:
                return {
                    "error": f"No billing information found for customer {customer_id}.",
                }

            return dict(billing)

    except Exception as e:
        conn.rollback()
        logger.error(f"Error getting billing info: {e}")
        raise
    finally:
        conn.close()


def process_refund(
    tenant_id: str,
    customer_id: str,
    amount: str,
    reason: str,
) -> dict:
    """
    Process a refund for a customer.
    Validates the amount against the tenant plan's refund limit.
    """
    refund_amount = Decimal(str(amount))

    if refund_amount <= 0:
        return {"error": "Refund amount must be positive."}

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            set_tenant_context(cur, tenant_id)

            # Get tenant plan to determine refund limit
            cur.execute(
                "SELECT plan FROM tenants WHERE tenant_id = %s",
                (tenant_id,),
            )
            tenant_row = cur.fetchone()
            plan = tenant_row["plan"] if tenant_row else "starter"
            refund_limit = REFUND_LIMITS.get(plan, DEFAULT_REFUND_LIMIT)

            if refund_amount > refund_limit:
                conn.commit()
                return {
                    "error": (
                        f"Refund amount ${refund_amount} exceeds the "
                        f"limit of ${refund_limit} for the '{plan}' plan. "
                        "Please escalate to a billing manager."
                    ),
                    "requires_escalation": True,
                    "refund_limit": float(refund_limit),
                }

            # Verify the customer exists and has billing
            cur.execute(
                """
                SELECT billing_id, amount AS current_amount
                FROM billing_info
                WHERE customer_id = %s
                """,
                (customer_id,),
            )
            billing = cur.fetchone()
            if not billing:
                conn.commit()
                return {"error": f"No billing record found for customer {customer_id}."}

            # Record the refund
            now = datetime.now(timezone.utc)
            cur.execute(
                """
                INSERT INTO refunds
                    (tenant_id, customer_id, amount, reason, status,
                     processed_by, created_at)
                VALUES (%s, %s, %s, %s, 'processed', 'agent', %s)
                RETURNING refund_id, amount, status, created_at
                """,
                (tenant_id, customer_id, refund_amount, reason, now),
            )

            refund = cur.fetchone()
            conn.commit()

            return {
                "message": "Refund processed successfully.",
                "refund": dict(refund),
            }

    except Exception as e:
        conn.rollback()
        logger.error(f"Error processing refund: {e}")
        raise
    finally:
        conn.close()


def get_invoice_history(
    tenant_id: str,
    customer_id: str,
    limit: int = 12,
) -> dict:
    """Get invoice history for a customer."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            set_tenant_context(cur, tenant_id)

            cur.execute(
                """
                SELECT invoice_id, customer_id, amount, currency,
                       invoice_date, due_date, paid_date, status,
                       description
                FROM invoices
                WHERE customer_id = %s
                ORDER BY invoice_date DESC
                LIMIT %s
                """,
                (customer_id, limit),
            )

            invoices = cur.fetchall()
            conn.commit()

            return {
                "total": len(invoices),
                "customer_id": customer_id,
                "invoices": [dict(inv) for inv in invoices],
            }

    except Exception as e:
        conn.rollback()
        logger.error(f"Error getting invoice history: {e}")
        raise
    finally:
        conn.close()


def lambda_handler(event, context):
    """AWS Lambda handler for billing inquiry gateway tool."""
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        action = event.get("action", "")
        params = event.get("parameters", {})
        tenant_id = params.get("tenant_id", "")

        if not tenant_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "tenant_id is required."}),
            }

        if action == "get_billing_info":
            customer_id = params.get("customer_id")
            if not customer_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "customer_id is required."}),
                }
            result = get_billing_info(tenant_id=tenant_id, customer_id=customer_id)

        elif action == "process_refund":
            customer_id = params.get("customer_id")
            amount = params.get("amount")
            reason = params.get("reason")
            if not all([customer_id, amount, reason]):
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "customer_id, amount, and reason are required.",
                    }),
                }
            result = process_refund(
                tenant_id=tenant_id,
                customer_id=customer_id,
                amount=amount,
                reason=reason,
            )

        elif action == "get_invoice_history":
            customer_id = params.get("customer_id")
            if not customer_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "customer_id is required."}),
                }
            result = get_invoice_history(
                tenant_id=tenant_id,
                customer_id=customer_id,
                limit=int(params.get("limit", 12)),
            )

        else:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Unknown action: {action}. "
                    "Valid actions: get_billing_info, process_refund, get_invoice_history",
                }),
            }

        return {
            "statusCode": 200,
            "body": json.dumps(result, cls=DecimalEncoder, ensure_ascii=False),
        }

    except Exception as e:
        logger.error(f"Lambda execution failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal error: {str(e)}"}),
        }
