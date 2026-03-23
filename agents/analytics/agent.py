"""
Analytics Agent for Multi-Tenant SaaS
Uses Strands Agent SDK with Code Interpreter for data analysis.
Generates ticket statistics, charts, and reports per tenant.
"""

import json
import logging
import os

from strands import Agent
from strands.models.bedrock import BedrockModel
from strands_tools import code_interpreter
from bedrock_agentcore.runtime import BedrockAgentCoreApp

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

SYSTEM_PROMPT = """あなたはマルチテナントSaaSプラットフォームのデータ分析エージェントです。
サポートチケットの統計、傾向分析、レポート生成を行います。

You are a data analytics agent for a multi-tenant SaaS platform.
You perform support ticket statistics, trend analysis, and report generation.

## 分析ガイドライン / Analysis Guidelines

1. **テナント分離 / Tenant Isolation**:
   - 分析は常に単一テナントのデータのみを対象としてください。
   - Always analyze data for a single tenant only.
   - テナント間のデータ比較は行わないでください。
   - Do NOT compare data across tenants.

2. **利用可能な分析 / Available Analyses**:
   - チケット統計（ステータス別、優先度別、カテゴリ別）
   - Ticket statistics (by status, priority, category)
   - 解決時間の分析
   - Resolution time analysis
   - トレンド分析（日次、週次、月次）
   - Trend analysis (daily, weekly, monthly)
   - SLA達成率
   - SLA compliance rate
   - 顧客満足度レポート
   - Customer satisfaction reports

3. **出力形式 / Output Format**:
   - データはテーブル形式で表示してください。
   - Display data in table format.
   - Code Interpreterを使用してグラフやチャートを生成してください。
   - Use Code Interpreter to generate graphs and charts.
   - 分析結果には必ずサマリーと推奨事項を含めてください。
   - Always include a summary and recommendations in analysis results.

4. **コード実行 / Code Execution**:
   - pandas, matplotlib, seaborn を使用してデータ分析を行ってください。
   - Use pandas, matplotlib, seaborn for data analysis.
   - グラフには日本語フォントの設定を含めてください（日本語テナントの場合）。
   - Include Japanese font configuration for graphs (for Japanese tenants).
"""

# Initialize the BedrockAgentCoreApp
app = BedrockAgentCoreApp()

# Configure the Bedrock model
model = BedrockModel(
    model_id="us.anthropic.claude-sonnet-4-6",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    temperature=0.2,
    max_tokens=4096,
)

# Sample ticket data for demo purposes.
# In production, this would be fetched from a database via gateway tools.
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


def extract_tenant_context(event: dict) -> dict:
    """Extract tenant context from the invocation event."""
    tenant_context = {}
    session_attrs = event.get("sessionAttributes", {})
    if session_attrs:
        tenant_context["tenant_id"] = session_attrs.get("tenantId", "")
        tenant_context["tenant_name"] = session_attrs.get("tenantName", "")
        tenant_context["plan"] = session_attrs.get("tenantPlan", "")

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
    Main entrypoint for the analytics agent.
    Called by Bedrock AgentCore Runtime.
    """
    logger.info("Received analytics request")

    tenant_context = extract_tenant_context(event)
    tenant_id = tenant_context.get("tenant_id", "unknown")
    logger.info(f"Processing analytics request for tenant: {tenant_id}")

    if not tenant_id or tenant_id == "unknown":
        return {
            "statusCode": 403,
            "body": json.dumps({
                "error": "Tenant context is required.",
                "error_ja": "テナントコンテキストが必要です。",
            }),
        }

    user_input = event.get("inputText", "")
    if not user_input:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "No input provided.",
                "error_ja": "入力が提供されていません。",
            }),
        }

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

    try:
        agent = Agent(
            model=model,
            system_prompt=enriched_prompt,
            tools=[code_interpreter],
        )

        response = agent(user_input)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "response": str(response),
                "tenantId": tenant_id,
            }),
        }

    except Exception as e:
        logger.error(f"Analytics agent failed for tenant {tenant_id}: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": f"An error occurred: {str(e)}",
                "error_ja": f"エラーが発生しました: {str(e)}",
            }),
        }


if __name__ == "__main__":
    app.run()
