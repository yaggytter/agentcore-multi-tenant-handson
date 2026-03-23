"""
Customer Support Agent for Multi-Tenant SaaS
Uses Strands Agent SDK with Amazon Bedrock AgentCore.
"""

import json
import logging
import os

from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools import retrieve
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from tools import get_customer_info, escalate_ticket, get_faq

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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

# Initialize the BedrockAgentCoreApp
app = BedrockAgentCoreApp()

# Configure the Bedrock model
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-6",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    temperature=0.3,
    max_tokens=4096,
)

# Combine custom tools with gateway tools
custom_tools = [get_customer_info, escalate_ticket, get_faq]


def build_agent(session_id: str = None, tenant_context: dict = None) -> Agent:
    """Build a customer support agent with memory and tenant context."""
    # Prepare tenant-aware system prompt
    tenant_prompt = SYSTEM_PROMPT
    if tenant_context:
        tenant_prompt += f"""

## 現在のテナント情報 / Current Tenant Context
- Tenant ID: {tenant_context.get('tenant_id', 'unknown')}
- Tenant Name: {tenant_context.get('tenant_name', 'unknown')}
- Plan: {tenant_context.get('plan', 'unknown')}
"""

    # Retrieve gateway tools from AgentCore
    gateway_tools = app.get_gateway_tools()

    agent = Agent(
        model=model,
        system_prompt=tenant_prompt,
        tools=[*custom_tools, *gateway_tools, retrieve],
    )

    # Attach memory if session_id is provided
    if session_id:
        memory_config = app.get_memory_config()
        if memory_config:
            agent.with_short_term_memory(
                memory_id=memory_config.get("stm_id"),
                session_id=session_id,
            )
            agent.with_long_term_memory(
                memory_id=memory_config.get("ltm_id"),
                namespace=tenant_context.get("tenant_id", "default")
                if tenant_context
                else "default",
            )

    return agent


def extract_tenant_context(event: dict) -> dict:
    """Extract tenant context from the invocation event (JWT claims)."""
    tenant_context = {}

    # Extract from session attributes (populated by interceptor)
    session_attrs = event.get("sessionAttributes", {})
    if session_attrs:
        tenant_context["tenant_id"] = session_attrs.get("tenantId", "")
        tenant_context["tenant_name"] = session_attrs.get("tenantName", "")
        tenant_context["plan"] = session_attrs.get("tenantPlan", "")

    # Fallback: extract from JWT claims in the request context
    request_context = event.get("requestContext", {})
    authorizer = request_context.get("authorizer", {})
    claims = authorizer.get("claims", {})
    if claims and not tenant_context.get("tenant_id"):
        tenant_context["tenant_id"] = claims.get("custom:tenantId", "")
        tenant_context["tenant_name"] = claims.get("custom:tenantName", "")
        tenant_context["plan"] = claims.get("custom:tenantPlan", "")

    return tenant_context


@app.entrypoint
def handle_request(event: dict, context: dict) -> dict:
    """
    Main entrypoint for the customer support agent.
    Called by Bedrock AgentCore Runtime.
    """
    logger.info("Received customer support request")

    # Extract tenant context
    tenant_context = extract_tenant_context(event)
    tenant_id = tenant_context.get("tenant_id", "unknown")
    logger.info(f"Processing request for tenant: {tenant_id}")

    if not tenant_id or tenant_id == "unknown":
        logger.warning("No tenant context found in request")
        return {
            "statusCode": 403,
            "body": json.dumps({
                "error": "Tenant context is required. Please authenticate.",
                "error_ja": "テナントコンテキストが必要です。認証してください。",
            }),
        }

    # Extract session and input
    session_id = event.get("sessionId", f"{tenant_id}-default")
    user_input = event.get("inputText", "")

    if not user_input:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "No input provided.",
                "error_ja": "入力が提供されていません。",
            }),
        }

    # Build and invoke the agent
    try:
        agent = build_agent(
            session_id=session_id,
            tenant_context=tenant_context,
        )
        response = agent(user_input)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "response": str(response),
                "sessionId": session_id,
                "tenantId": tenant_id,
            }),
        }

    except Exception as e:
        logger.error(f"Agent execution failed for tenant {tenant_id}: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": f"An error occurred: {str(e)}",
                "error_ja": f"エラーが発生しました: {str(e)}",
            }),
        }


if __name__ == "__main__":
    app.run()
