"""
Gateway Tool Lambda: Ticket Management
CRUD operations for support tickets with tenant isolation via RLS.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "support")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_SECRET_ARN = os.environ.get("DB_SECRET_ARN")


def get_connection():
    """Create a database connection with RLS-ready configuration."""
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


def list_tickets(tenant_id: str, status_filter: str = None) -> dict:
    """List support tickets for a tenant, optionally filtered by status."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            set_tenant_context(cur, tenant_id)

            if status_filter:
                cur.execute(
                    """
                    SELECT ticket_id, subject, status, priority, category,
                           created_at, updated_at, assigned_to
                    FROM support_tickets
                    WHERE status = %s
                    ORDER BY created_at DESC
                    """,
                    (status_filter,),
                )
            else:
                cur.execute(
                    """
                    SELECT ticket_id, subject, status, priority, category,
                           created_at, updated_at, assigned_to
                    FROM support_tickets
                    ORDER BY created_at DESC
                    """
                )

            tickets = cur.fetchall()
            conn.commit()

            # Convert datetime objects to strings
            for ticket in tickets:
                for key, value in ticket.items():
                    if isinstance(value, datetime):
                        ticket[key] = value.isoformat()

            return {
                "total": len(tickets),
                "tickets": tickets,
            }
    except Exception as e:
        conn.rollback()
        logger.error(f"Error listing tickets: {e}")
        raise
    finally:
        conn.close()


def get_ticket(tenant_id: str, ticket_id: str) -> dict:
    """Get a single ticket by ID."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            set_tenant_context(cur, tenant_id)

            cur.execute(
                """
                SELECT ticket_id, subject, description, status, priority,
                       category, created_at, updated_at, assigned_to,
                       resolution, resolved_at, customer_id
                FROM support_tickets
                WHERE ticket_id = %s
                """,
                (ticket_id,),
            )

            ticket = cur.fetchone()
            conn.commit()

            if not ticket:
                return {"error": f"Ticket {ticket_id} not found."}

            for key, value in ticket.items():
                if isinstance(value, datetime):
                    ticket[key] = value.isoformat()

            return ticket
    except Exception as e:
        conn.rollback()
        logger.error(f"Error getting ticket: {e}")
        raise
    finally:
        conn.close()


def create_ticket(
    tenant_id: str,
    subject: str,
    description: str,
    priority: str = "medium",
    category: str = "general",
    customer_id: str = None,
) -> dict:
    """Create a new support ticket."""
    valid_priorities = {"low", "medium", "high", "critical"}
    if priority not in valid_priorities:
        return {"error": f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"}

    valid_categories = {"general", "technical", "billing", "account", "feature_request"}
    if category not in valid_categories:
        return {"error": f"Invalid category. Must be one of: {', '.join(valid_categories)}"}

    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc)

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            set_tenant_context(cur, tenant_id)

            cur.execute(
                """
                INSERT INTO support_tickets
                    (ticket_id, tenant_id, subject, description, status,
                     priority, category, customer_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 'open', %s, %s, %s, %s, %s)
                RETURNING ticket_id, subject, status, priority, category, created_at
                """,
                (ticket_id, tenant_id, subject, description,
                 priority, category, customer_id, now, now),
            )

            new_ticket = cur.fetchone()
            conn.commit()

            for key, value in new_ticket.items():
                if isinstance(value, datetime):
                    new_ticket[key] = value.isoformat()

            return {
                "message": "Ticket created successfully.",
                "ticket": new_ticket,
            }
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating ticket: {e}")
        raise
    finally:
        conn.close()


def update_ticket(
    tenant_id: str,
    ticket_id: str,
    status: str = None,
    resolution: str = None,
    assigned_to: str = None,
    priority: str = None,
) -> dict:
    """Update a support ticket's status, resolution, or assignment."""
    valid_statuses = {"open", "in_progress", "waiting_on_customer", "resolved", "closed"}
    if status and status not in valid_statuses:
        return {"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}

    now = datetime.now(timezone.utc)

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            set_tenant_context(cur, tenant_id)

            # Build dynamic update
            updates = ["updated_at = %s"]
            params = [now]

            if status:
                updates.append("status = %s")
                params.append(status)
                if status in ("resolved", "closed"):
                    updates.append("resolved_at = %s")
                    params.append(now)

            if resolution:
                updates.append("resolution = %s")
                params.append(resolution)

            if assigned_to:
                updates.append("assigned_to = %s")
                params.append(assigned_to)

            if priority:
                updates.append("priority = %s")
                params.append(priority)

            params.append(ticket_id)

            cur.execute(
                f"""
                UPDATE support_tickets
                SET {', '.join(updates)}
                WHERE ticket_id = %s
                RETURNING ticket_id, subject, status, priority, resolution,
                          assigned_to, updated_at, resolved_at
                """,
                params,
            )

            updated_ticket = cur.fetchone()
            conn.commit()

            if not updated_ticket:
                return {"error": f"Ticket {ticket_id} not found."}

            for key, value in updated_ticket.items():
                if isinstance(value, datetime):
                    updated_ticket[key] = value.isoformat()

            return {
                "message": "Ticket updated successfully.",
                "ticket": updated_ticket,
            }
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating ticket: {e}")
        raise
    finally:
        conn.close()


def lambda_handler(event, context):
    """AWS Lambda handler for ticket management gateway tool."""
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Extract parameters from the gateway tool invocation
        action = event.get("action", "")
        params = event.get("parameters", {})
        tenant_id = params.get("tenant_id", "")

        if not tenant_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "tenant_id is required."}),
            }

        if action == "list_tickets":
            result = list_tickets(
                tenant_id=tenant_id,
                status_filter=params.get("status_filter"),
            )
        elif action == "get_ticket":
            ticket_id = params.get("ticket_id")
            if not ticket_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "ticket_id is required."}),
                }
            result = get_ticket(tenant_id=tenant_id, ticket_id=ticket_id)
        elif action == "create_ticket":
            subject = params.get("subject")
            description = params.get("description", "")
            if not subject:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "subject is required."}),
                }
            result = create_ticket(
                tenant_id=tenant_id,
                subject=subject,
                description=description,
                priority=params.get("priority", "medium"),
                category=params.get("category", "general"),
                customer_id=params.get("customer_id"),
            )
        elif action == "update_ticket":
            ticket_id = params.get("ticket_id")
            if not ticket_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "ticket_id is required."}),
                }
            result = update_ticket(
                tenant_id=tenant_id,
                ticket_id=ticket_id,
                status=params.get("status"),
                resolution=params.get("resolution"),
                assigned_to=params.get("assigned_to"),
                priority=params.get("priority"),
            )
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Unknown action: {action}. "
                    "Valid actions: list_tickets, get_ticket, create_ticket, update_ticket",
                }),
            }

        return {
            "statusCode": 200,
            "body": json.dumps(result, default=str, ensure_ascii=False),
        }

    except Exception as e:
        logger.error(f"Lambda execution failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Internal error: {str(e)}"}),
        }
