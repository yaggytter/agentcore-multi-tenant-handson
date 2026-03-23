"""
Gateway Tool Lambda: Knowledge Search
Search and retrieve tenant-specific FAQ and knowledge articles.
Uses PostgreSQL full-text search for efficient querying.
"""

import json
import logging
import os
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "support")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")


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


def search_articles(tenant_id: str, query: str, category: str = None, limit: int = 10) -> dict:
    """
    Search knowledge articles using PostgreSQL full-text search.
    Supports both Japanese and English content via the configured text search config.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            set_tenant_context(cur, tenant_id)

            # Build the search query using full-text search
            # ts_vector is assumed to be a generated column or maintained via trigger
            if query:
                sql = """
                    SELECT article_id, title, content, category, tags,
                           created_at, updated_at,
                           ts_rank(search_vector, plainto_tsquery('simple', %s)) AS relevance
                    FROM knowledge_articles
                    WHERE search_vector @@ plainto_tsquery('simple', %s)
                """
                params = [query, query]

                if category:
                    sql += " AND category = %s"
                    params.append(category)

                sql += " ORDER BY relevance DESC LIMIT %s"
                params.append(limit)
            else:
                # No query: return recent articles
                sql = """
                    SELECT article_id, title, content, category, tags,
                           created_at, updated_at
                    FROM knowledge_articles
                """
                params = []

                if category:
                    sql += " WHERE category = %s"
                    params.append(category)

                sql += " ORDER BY updated_at DESC LIMIT %s"
                params.append(limit)

            cur.execute(sql, params)
            articles = cur.fetchall()
            conn.commit()

            # Convert datetime objects
            for article in articles:
                for key, value in article.items():
                    if isinstance(value, datetime):
                        article[key] = value.isoformat()

            return {
                "total": len(articles),
                "query": query,
                "articles": articles,
            }

    except Exception as e:
        conn.rollback()
        logger.error(f"Error searching articles: {e}")
        raise
    finally:
        conn.close()


def get_article(tenant_id: str, article_id: str) -> dict:
    """Get a single knowledge article by ID."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            set_tenant_context(cur, tenant_id)

            cur.execute(
                """
                SELECT article_id, title, content, category, tags,
                       author, created_at, updated_at, view_count
                FROM knowledge_articles
                WHERE article_id = %s
                """,
                (article_id,),
            )

            article = cur.fetchone()

            if not article:
                conn.commit()
                return {"error": f"Article {article_id} not found."}

            # Increment view count
            cur.execute(
                """
                UPDATE knowledge_articles
                SET view_count = view_count + 1
                WHERE article_id = %s
                """,
                (article_id,),
            )
            conn.commit()

            for key, value in article.items():
                if isinstance(value, datetime):
                    article[key] = value.isoformat()

            return article

    except Exception as e:
        conn.rollback()
        logger.error(f"Error getting article: {e}")
        raise
    finally:
        conn.close()


def lambda_handler(event, context):
    """AWS Lambda handler for knowledge search gateway tool."""
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

        if action == "search_articles":
            query = params.get("query", "")
            result = search_articles(
                tenant_id=tenant_id,
                query=query,
                category=params.get("category"),
                limit=int(params.get("limit", 10)),
            )
        elif action == "get_article":
            article_id = params.get("article_id")
            if not article_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "article_id is required."}),
                }
            result = get_article(tenant_id=tenant_id, article_id=article_id)
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Unknown action: {action}. "
                    "Valid actions: search_articles, get_article",
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
