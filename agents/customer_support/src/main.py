"""
Customer Support Agent for Multi-Tenant SaaS
Uses Strands Agent SDK with Amazon Bedrock AgentCore.
"""

import json
import logging
import os

from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from tools import get_customer_info, escalate_ticket, get_faq

app = BedrockAgentCoreApp()
log = app.logger

REGION = os.getenv("AWS_REGION", "us-east-1")

SYSTEM_PROMPT = """あなたはマルチテナントSaaSプラットフォームのカスタマーサポートエージェントです。
お客様からの問い合わせに対して、丁寧かつ正確にサポートを提供してください。

You are a customer support agent for a multi-tenant SaaS platform.
Provide polite and accurate support for customer inquiries.

## 対応ガイドライン / Response Guidelines

1. **言語対応 / Language**:
   - お客様の言語に合わせて日本語または英語で対応してください。
   - Respond in the same language the customer uses (Japanese or English).

2. **テナント分離 / Tenant Isolation**:
   - 常に現在のテナントコンテキストを確認し、テナント固有の情報のみを参照してください。
   - Always verify the current tenant context and only reference tenant-specific information.
   - 他のテナントの情報は絶対に開示しないでください。
   - NEVER disclose information belonging to other tenants.

3. **対応フロー / Support Flow**:
   a. まず顧客情報を確認する / First verify customer information
   b. FAQやナレッジベースを検索する / Search FAQ and knowledge base
   c. チケット管理ツールで既存のチケットを確認する / Check existing tickets
   d. 必要に応じて新規チケットを作成する / Create new tickets as needed
   e. 解決できない場合はエスカレーションする / Escalate if unable to resolve

4. **請求関連 / Billing**:
   - 返金処理は慎重に行い、必ず理由を記録してください。
   - Process refunds carefully and always record the reason.
   - 返金上限を超える場合はエスカレーションしてください。
   - Escalate if the refund exceeds the limit.

5. **メモリ活用 / Memory Usage**:
   - 短期記憶で会話のコンテキストを維持してください。
   - Use short-term memory to maintain conversation context.
   - 重要な顧客の好みや過去のやり取りは長期記憶に保存してください。
   - Store important customer preferences and past interactions in long-term memory.
"""


def extract_tenant_context(payload: dict) -> dict:
    """Extract tenant context from the invocation payload (JWT claims)."""
    tenant_context = {}

    # Extract from session attributes (populated by interceptor)
    session_attrs = payload.get("sessionAttributes", {})
    if session_attrs:
        tenant_context["tenant_id"] = session_attrs.get("tenantId", "")
        tenant_context["tenant_name"] = session_attrs.get("tenantName", "")
        tenant_context["plan"] = session_attrs.get("tenantPlan", "")

    # Fallback: extract from JWT claims in the request context
    request_context = payload.get("requestContext", {})
    authorizer = request_context.get("authorizer", {})
    claims = authorizer.get("claims", {})
    if claims and not tenant_context.get("tenant_id"):
        tenant_context["tenant_id"] = claims.get("custom:tenantId", "")
        tenant_context["tenant_name"] = claims.get("custom:tenantName", "")
        tenant_context["plan"] = claims.get("custom:tenantPlan", "")

    return tenant_context


@app.entrypoint
async def invoke(payload, context):
    session_id = getattr(context, 'session_id', 'default')
    user_id = payload.get("user_id") or 'default-user'

    # Extract tenant context
    tenant_context = extract_tenant_context(payload)
    tenant_id = tenant_context.get("tenant_id", "unknown")
    log.info(f"Processing request for tenant: {tenant_id}")

    # Build tenant-aware system prompt
    tenant_prompt = SYSTEM_PROMPT
    if tenant_context.get("tenant_id"):
        tenant_prompt += f"""

## 現在のテナント情報 / Current Tenant Context
- Tenant ID: {tenant_context.get('tenant_id', 'unknown')}
- Tenant Name: {tenant_context.get('tenant_name', 'unknown')}
- Plan: {tenant_context.get('plan', 'unknown')}
"""

    # Create agent with model and tools
    agent = Agent(
        model=load_model(),
        system_prompt=tenant_prompt,
        tools=[get_customer_info, escalate_ticket, get_faq],
    )

    # Execute and stream response
    stream = agent.stream_async(payload.get("prompt", "Hello!"))

    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
