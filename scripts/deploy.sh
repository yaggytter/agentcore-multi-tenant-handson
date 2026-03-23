#!/bin/bash
# =============================================================================
# Deployment Script for AgentCore Multi-Tenant Hands-on
# =============================================================================
# Deploys CDK stacks incrementally by chapter number.
#
# Usage:
#   ./scripts/deploy.sh <chapter>
#
# Chapters:
#   1    - VPC + Supporting infrastructure
#   2    - + Gateway + Lambda tools
#   3    - + Memory
#   4    - + Cognito (authentication)
#   5    - + Database (RDS + seed data)
#   full - All stacks at once
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CDK_DIR="${PROJECT_ROOT}/cdk"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${BLUE}[STEP]${NC} $1"; }

# Stack names
STACK_VPC="AgentCoreVpcStack"
STACK_SUPPORTING="AgentCoreSupportingStack"
STACK_GATEWAY="AgentCoreGatewayStack"
STACK_LAMBDA="AgentCoreLambdaToolsStack"
STACK_MEMORY="AgentCoreMemoryStack"
STACK_COGNITO="AgentCoreCognitoStack"
STACK_DATABASE="AgentCoreDatabaseStack"

# -----------------------------------------------------------------------------
# Usage
# -----------------------------------------------------------------------------
usage() {
    echo "Usage: $0 <chapter>"
    echo ""
    echo "Chapters:"
    echo "  1    - VPC + Supporting infrastructure"
    echo "  2    - + Gateway + Lambda tools"
    echo "  3    - + Memory"
    echo "  4    - + Cognito (authentication)"
    echo "  5    - + Database (RDS + seed data)"
    echo "  full - All stacks at once"
    exit 1
}

# -----------------------------------------------------------------------------
# Deploy stacks
# -----------------------------------------------------------------------------
deploy_stacks() {
    local stacks=("$@")
    log_info "Deploying stacks: ${stacks[*]}"

    cd "${CDK_DIR}"

    # Activate virtual environment if it exists
    if [ -f "${PROJECT_ROOT}/.venv/bin/activate" ]; then
        source "${PROJECT_ROOT}/.venv/bin/activate"
    fi

    cdk deploy "${stacks[@]}" \
        --require-approval never \
        --outputs-file "${PROJECT_ROOT}/cdk-outputs.json"

    log_info "Deployment complete."
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    if [ $# -lt 1 ]; then
        usage
    fi

    local chapter="$1"

    echo "============================================================"
    echo "  AgentCore Multi-Tenant Hands-on - Deploy"
    echo "  Chapter: ${chapter}"
    echo "============================================================"
    echo ""

    case "${chapter}" in
        1)
            log_step "Chapter 1: Deploying VPC + Supporting infrastructure"
            deploy_stacks "${STACK_VPC}" "${STACK_SUPPORTING}"
            ;;
        2)
            log_step "Chapter 2: Deploying Gateway + Lambda tools"
            log_info "(Includes Chapter 1 stacks as dependencies)"
            deploy_stacks "${STACK_VPC}" "${STACK_SUPPORTING}" \
                          "${STACK_GATEWAY}" "${STACK_LAMBDA}"
            ;;
        3)
            log_step "Chapter 3: Deploying Memory"
            log_info "(Includes Chapters 1-2 stacks as dependencies)"
            deploy_stacks "${STACK_VPC}" "${STACK_SUPPORTING}" \
                          "${STACK_GATEWAY}" "${STACK_LAMBDA}" \
                          "${STACK_MEMORY}"
            ;;
        4)
            log_step "Chapter 4: Deploying Cognito (authentication)"
            log_info "(Includes Chapters 1-3 stacks as dependencies)"
            deploy_stacks "${STACK_VPC}" "${STACK_SUPPORTING}" \
                          "${STACK_GATEWAY}" "${STACK_LAMBDA}" \
                          "${STACK_MEMORY}" "${STACK_COGNITO}"
            ;;
        5)
            log_step "Chapter 5: Deploying Database (RDS + seed data)"
            log_info "(Includes Chapters 1-4 stacks as dependencies)"
            deploy_stacks "${STACK_VPC}" "${STACK_SUPPORTING}" \
                          "${STACK_GATEWAY}" "${STACK_LAMBDA}" \
                          "${STACK_MEMORY}" "${STACK_COGNITO}" \
                          "${STACK_DATABASE}"
            ;;
        full)
            log_step "Full deployment: All stacks"
            deploy_stacks "${STACK_VPC}" "${STACK_SUPPORTING}" \
                          "${STACK_GATEWAY}" "${STACK_LAMBDA}" \
                          "${STACK_MEMORY}" "${STACK_COGNITO}" \
                          "${STACK_DATABASE}"
            ;;
        *)
            log_error "Unknown chapter: ${chapter}"
            usage
            ;;
    esac

    echo ""
    echo "============================================================"
    log_info "Chapter ${chapter} deployment finished."
    if [ -f "${PROJECT_ROOT}/cdk-outputs.json" ]; then
        log_info "Stack outputs saved to: ${PROJECT_ROOT}/cdk-outputs.json"
    fi
    echo "============================================================"
}

main "$@"
