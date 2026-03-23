"""
Analytics Agent for Multi-Tenant SaaS
Uses Strands Agent SDK with Code Interpreter for data analysis.
Generates ticket statistics, charts, and reports per tenant.
"""

import json
import logging
import os

from strands import Agent
from strands_tools.code_interpreter import AgentCoreCodeInterpreter
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger

REGION = os.getenv("AWS_REGION", "us-east-1")

SYSTEM_PROMPT = """あなたはマルチテナントSaaSプラットフォームのデータ分析エージェントです。
サポートチケットの統計、傾向分析、レポート生成を行います。

You are a data analytics agent for a multi-tenant SaaS platform.
You perform support ticket statistics, trend analysis, and report generation.

## 分析ガイドライン / Analysis Guidelines

1. **テナント分離 / Tenant Isolation**:
   - 分析は常に単一テナントのデータのみを対象としてください。
   - Always analyze data for a single tenant only.

2. **利用可能な分析 / Available Analyses**:
   - チケット統計（ステータス別、優先度別、カテゴリ別）
   - 解決時間の分析
   - トレンド分析（日次、週次、月次）
   - SLA達成率
   - 顧客満足度レポート

3. **出力形式 / Output Format**:
   - Code Interpreterを使用してグラフやチャートを生成してください。
   - 分析結果には必ずサマリーと推奨事項を含めてください。

4. **コード実行 / Code Execution**:
   - pandas, matplotlib, seaborn を使用してデータ分析を行ってください。
"""

# Sample ticket data for demo purposes
SAMPLE_TICKET_DATA = {
    "tenant-a": {
        "tickets": [
            {"id": "TKT-A001", "status": "open", "priority": "high", "category": "billing", "created": "2025-12-01", "resolved": None, "satisfaction": None},
            {"id": "TKT-A002", "status": "resolved", "priority": "medium", "category": "technical", "created": "2025-12-02", "resolved": "2025-12-03", "satisfaction": 4},
            {"id": "TKT-A003", "status": "resolved", "priority": "low", "category": "account", "created": "2025-12-03", "resolved": "2025-12-03", "satisfaction": 5},
            {"id": "TKT-A004", "status": "in_progress", "priority": "high", "category": "technical", "created": "2025-12-04", "resolved": None, "satisfaction": None},
            {"id": "TKT-A005", "status": "resolved", "priority": "medium", "category": "billing", "created": "2025-12-05", "resolved": "2025-12-06", "satisfaction": 3},
            {"id": "TKT-A006", "status": "open", "priority": "critical", "category": "technical", "created": "2025-12-06", "resolved": None, "satisfaction": None},
            {"id": "TKT-A007", "status": "resolved", "priority": "low", "category": "account", "created": "2025-12-07", "resolved": "2025-12-07", "satisfaction": 5},
            {"id": "TKT-A008", "status": "resolved", "priority": "medium", "category": "technical", "created": "2025-12-08", "resolved": "2025-12-10", "satisfaction": 4},
            {"id": "TKT-A009", "status": "in_progress", "priority": "high", "category": "billing", "created": "2025-12-09", "resolved": None, "satisfaction": None},
            {"id": "TKT-A010", "status": "open", "priority": "medium", "category": "account", "created": "2025-12-10", "resolved": None, "satisfaction": None},
        ],
    },
    "tenant-b": {
        "tickets": [
            {"id": "TKT-B001", "status": "resolved", "priority": "low", "category": "account", "created": "2025-12-01", "resolved": "2025-12-01", "satisfaction": 5},
            {"id": "TKT-B002", "status": "resolved", "priority": "medium", "category": "technical", "created": "2025-12-02", "resolved": "2025-12-04", "satisfaction": 3},
            {"id": "TKT-B003", "status": "open", "priority": "high", "category": "billing", "created": "2025-12-03", "resolved": None, "satisfaction": None},
            {"id": "TKT-B004", "status": "resolved", "priority": "medium", "category": "account", "created": "2025-12-04", "resolved": "2025-12-05", "satisfaction": 4},
            {"id": "TKT-B005", "status": "in_progress", "priority": "critical", "category": "technical", "created": "2025-12-05", "resolved": None, "satisfaction": None},
            {"id": "TKT-B006", "status": "resolved", "priority": "low", "category": "billing", "created": "2025-12-06", "resolved": "2025-12-06", "satisfaction": 5},
            {"id": "TKT-B007", "status": "open", "priority": "medium", "category": "technical", "created": "2025-12-07", "resolved": None, "satisfaction": None},
        ],
    },
}


def get_ticket_data_as_context(tenant_id: str) -> str:
    """Prepare ticket data as context string for the agent."""
    tenant_data = SAMPLE_TICKET_DATA.get(tenant_id)
    if not tenant_data:
        return "No ticket data available for this tenant."
    return json.dumps(tenant_data["tickets"], indent=2, ensure_ascii=False)


def extract_tenant_context(payload: dict) -> dict:
    """Extract tenant context from the invocation payload."""
    tenant_context = {}
    session_attrs = payload.get("sessionAttributes", {})
    if session_attrs:
        tenant_context["tenant_id"] = session_attrs.get("tenantId", "")
        tenant_context["tenant_name"] = session_attrs.get("tenantName", "")
        tenant_context["plan"] = session_attrs.get("tenantPlan", "")

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

    # Extract tenant context
    tenant_context = extract_tenant_context(payload)
    tenant_id = tenant_context.get("tenant_id", "unknown")
    log.info(f"Processing analytics request for tenant: {tenant_id}")

    # Prepare context with ticket data
    ticket_data = get_ticket_data_as_context(tenant_id)
    enriched_prompt = SYSTEM_PROMPT + f"""

## 現在のテナントデータ / Current Tenant Data
Tenant ID: {tenant_id}
Tenant Name: {tenant_context.get('tenant_name', 'unknown')}

以下はこのテナントのチケットデータです。分析に使用してください。
Below is the ticket data for this tenant. Use it for analysis.

```json
{ticket_data}
```
"""

    # Create code interpreter
    code_interpreter = AgentCoreCodeInterpreter(
        region=REGION,
        session_name=session_id,
        auto_create=True,
        persist_sessions=True,
    )

    # Create agent
    agent = Agent(
        model=load_model(),
        system_prompt=enriched_prompt,
        tools=[code_interpreter.code_interpreter],
    )

    # Execute and stream response
    stream = agent.stream_async(payload.get("prompt", "チケットの統計を分析してください"))

    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
