"""
VPC Stack for AgentCore Multi-Tenant Hands-on

Creates a VPC with public/private subnets, NAT Gateway,
and security groups for Aurora PostgreSQL and Lambda functions.
"""

from aws_cdk import (
    Stack,
    CfnOutput,
    aws_ec2 as ec2,
)
from constructs import Construct


class VpcStack(Stack):
    """VPC infrastructure for the multi-tenant SaaS platform."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # -----------------------------------------------------------
        # VPC with public and private subnets across 2 AZs
        # NAT Gateway is single (cost optimization for hands-on)
        # -----------------------------------------------------------
        self.vpc = ec2.Vpc(
            self,
            "AgentCoreVpc",
            vpc_name="agentcore-multi-tenant-vpc",
            max_azs=2,
            nat_gateways=1,
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        # -----------------------------------------------------------
        # Security Group for Aurora PostgreSQL
        # Allows inbound PostgreSQL (5432) from Lambda SG only
        # -----------------------------------------------------------
        self.aurora_security_group = ec2.SecurityGroup(
            self,
            "AuroraSecurityGroup",
            vpc=self.vpc,
            security_group_name="agentcore-aurora-sg",
            description="Security group for Aurora PostgreSQL cluster",
            allow_all_outbound=False,
        )

        # -----------------------------------------------------------
        # Security Group for Lambda functions
        # Allows outbound to Aurora and internet (via NAT)
        # -----------------------------------------------------------
        self.lambda_security_group = ec2.SecurityGroup(
            self,
            "LambdaSecurityGroup",
            vpc=self.vpc,
            security_group_name="agentcore-lambda-sg",
            description="Security group for Lambda functions accessing Aurora",
            allow_all_outbound=True,
        )

        # Allow Lambda to connect to Aurora on PostgreSQL port
        self.aurora_security_group.add_ingress_rule(
            peer=self.lambda_security_group,
            connection=ec2.Port.tcp(5432),
            description="Allow Lambda functions to connect to Aurora PostgreSQL",
        )

        # -----------------------------------------------------------
        # VPC Endpoints for AWS services (reduces NAT costs)
        # -----------------------------------------------------------
        # S3 Gateway Endpoint (free)
        self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        # -----------------------------------------------------------
        # Outputs
        # -----------------------------------------------------------
        CfnOutput(
            self,
            "VpcId",
            value=self.vpc.vpc_id,
            description="VPC ID",
            export_name="AgentCoreVpcId",
        )

        CfnOutput(
            self,
            "AuroraSecurityGroupId",
            value=self.aurora_security_group.security_group_id,
            description="Aurora Security Group ID",
            export_name="AgentCoreAuroraSgId",
        )

        CfnOutput(
            self,
            "LambdaSecurityGroupId",
            value=self.lambda_security_group.security_group_id,
            description="Lambda Security Group ID",
            export_name="AgentCoreLambdaSgId",
        )
