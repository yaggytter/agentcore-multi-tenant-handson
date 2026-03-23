"""
Observability Stack for AgentCore Multi-Tenant Hands-on

Creates CloudWatch dashboard for agent metrics, alarms for error rates,
and log groups for all AgentCore components.
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    Duration,
    RemovalPolicy,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_logs as logs,
    aws_sns as sns,
)
from constructs import Construct


class ObservabilityStack(Stack):
    """CloudWatch dashboard, alarms, and log groups for AgentCore."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        gateway_id: str,
        runtime_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # -----------------------------------------------------------
        # Log Groups for AgentCore components
        # Centralized logging with 2-week retention for hands-on
        # -----------------------------------------------------------
        self.gateway_log_group = logs.LogGroup(
            self,
            "GatewayLogGroup",
            log_group_name="/aws/agentcore/gateway",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.runtime_log_group = logs.LogGroup(
            self,
            "RuntimeLogGroup",
            log_group_name="/aws/agentcore/runtime",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.tools_log_group = logs.LogGroup(
            self,
            "ToolsLogGroup",
            log_group_name="/aws/agentcore/tools",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.interceptor_log_group = logs.LogGroup(
            self,
            "InterceptorLogGroup",
            log_group_name="/aws/agentcore/interceptor",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # -----------------------------------------------------------
        # SNS Topic for alarm notifications
        # -----------------------------------------------------------
        self.alarm_topic = sns.Topic(
            self,
            "AlarmTopic",
            topic_name="agentcore-alarms",
            display_name="AgentCore Multi-Tenant Alarms",
        )

        # -----------------------------------------------------------
        # CloudWatch Metrics (custom namespace for AgentCore)
        # -----------------------------------------------------------
        namespace = "AgentCore/MultiTenant"

        # Metric: Agent invocation count
        invocation_metric = cloudwatch.Metric(
            namespace=namespace,
            metric_name="AgentInvocations",
            dimensions_map={"GatewayId": gateway_id},
            statistic="Sum",
            period=Duration.minutes(5),
        )

        # Metric: Agent invocation errors
        error_metric = cloudwatch.Metric(
            namespace=namespace,
            metric_name="AgentErrors",
            dimensions_map={"GatewayId": gateway_id},
            statistic="Sum",
            period=Duration.minutes(5),
        )

        # Metric: Agent latency (p99)
        latency_metric = cloudwatch.Metric(
            namespace=namespace,
            metric_name="AgentLatency",
            dimensions_map={"RuntimeId": runtime_id},
            statistic="p99",
            period=Duration.minutes(5),
        )

        # Metric: Tool invocation count
        tool_invocation_metric = cloudwatch.Metric(
            namespace=namespace,
            metric_name="ToolInvocations",
            dimensions_map={"GatewayId": gateway_id},
            statistic="Sum",
            period=Duration.minutes(5),
        )

        # Metric: Per-tenant invocations
        tenant_a_metric = cloudwatch.Metric(
            namespace=namespace,
            metric_name="AgentInvocations",
            dimensions_map={"TenantId": "tenant-a"},
            statistic="Sum",
            period=Duration.minutes(5),
        )

        tenant_b_metric = cloudwatch.Metric(
            namespace=namespace,
            metric_name="AgentInvocations",
            dimensions_map={"TenantId": "tenant-b"},
            statistic="Sum",
            period=Duration.minutes(5),
        )

        # -----------------------------------------------------------
        # Alarms
        # -----------------------------------------------------------

        # Alarm: High error rate (more than 10 errors in 5 minutes)
        error_alarm = cloudwatch.Alarm(
            self,
            "HighErrorRateAlarm",
            alarm_name="agentcore-high-error-rate",
            alarm_description="AgentCore agent error rate exceeds threshold",
            metric=error_metric,
            threshold=10,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        error_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        # Alarm: High latency (p99 > 30 seconds)
        latency_alarm = cloudwatch.Alarm(
            self,
            "HighLatencyAlarm",
            alarm_name="agentcore-high-latency",
            alarm_description="AgentCore agent p99 latency exceeds 30s",
            metric=latency_metric,
            threshold=30000,  # 30 seconds in milliseconds
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        latency_alarm.add_alarm_action(cw_actions.SnsAction(self.alarm_topic))

        # -----------------------------------------------------------
        # CloudWatch Dashboard
        # -----------------------------------------------------------
        dashboard = cloudwatch.Dashboard(
            self,
            "AgentCoreDashboard",
            dashboard_name="AgentCore-MultiTenant-Dashboard",
            default_interval=Duration.hours(3),
        )

        # Row 1: Overview metrics
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Agent Invocations",
                left=[invocation_metric],
                width=8,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="Agent Errors",
                left=[error_metric],
                width=8,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="Agent Latency (p99)",
                left=[latency_metric],
                width=8,
                height=6,
            ),
        )

        # Row 2: Per-tenant breakdown and tool usage
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Invocations by Tenant",
                left=[tenant_a_metric, tenant_b_metric],
                width=12,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="Tool Invocations",
                left=[tool_invocation_metric],
                width=12,
                height=6,
            ),
        )

        # Row 3: Lambda metrics for tool functions
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Tool Lambda Duration",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Duration",
                        dimensions_map={"FunctionName": "agentcore-tool-ticket-management"},
                        statistic="Average",
                        period=Duration.minutes(5),
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Duration",
                        dimensions_map={"FunctionName": "agentcore-tool-knowledge-search"},
                        statistic="Average",
                        period=Duration.minutes(5),
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Duration",
                        dimensions_map={"FunctionName": "agentcore-tool-billing-inquiry"},
                        statistic="Average",
                        period=Duration.minutes(5),
                    ),
                ],
                width=12,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="Tool Lambda Errors",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Errors",
                        dimensions_map={"FunctionName": "agentcore-tool-ticket-management"},
                        statistic="Sum",
                        period=Duration.minutes(5),
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Errors",
                        dimensions_map={"FunctionName": "agentcore-tool-knowledge-search"},
                        statistic="Sum",
                        period=Duration.minutes(5),
                    ),
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Errors",
                        dimensions_map={"FunctionName": "agentcore-tool-billing-inquiry"},
                        statistic="Sum",
                        period=Duration.minutes(5),
                    ),
                ],
                width=12,
                height=6,
            ),
        )

        # Row 4: Alarm status
        dashboard.add_widgets(
            cloudwatch.AlarmStatusWidget(
                title="Alarm Status",
                alarms=[error_alarm, latency_alarm],
                width=24,
                height=3,
            ),
        )

        # -----------------------------------------------------------
        # Outputs
        # -----------------------------------------------------------
        CfnOutput(
            self,
            "DashboardUrl",
            value=f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name=AgentCore-MultiTenant-Dashboard",
            description="CloudWatch Dashboard URL",
        )

        CfnOutput(
            self,
            "AlarmTopicArn",
            value=self.alarm_topic.topic_arn,
            description="SNS topic ARN for alarm notifications",
            export_name="AgentCoreAlarmTopicArn",
        )
