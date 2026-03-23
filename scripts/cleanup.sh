#!/bin/bash
# =============================================================================
# Cleanup Script for AgentCore Multi-Tenant Hands-on
# =============================================================================
# Destroys all CDK stacks, deletes ECR images, CloudWatch log groups,
# and deregisters Runtime agents.
#
# Usage:
#   ./scripts/cleanup.sh [--force]
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CDK_DIR="${PROJECT_ROOT}/cdk"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

FORCE=false
if [[ "${1:-}" == "--force" ]]; then
    FORCE=true
fi

# -----------------------------------------------------------------------------
# Confirmation prompt
# -----------------------------------------------------------------------------
confirm_cleanup() {
    if [ "$FORCE" = true ]; then
        return 0
    fi

    echo ""
    echo "WARNING: This will destroy ALL resources created by this hands-on."
    echo "This action cannot be undone."
    echo ""
    read -p "Are you sure you want to proceed? (yes/no): " confirmation
    if [[ "${confirmation}" != "yes" ]]; then
        echo "Cleanup cancelled."
        exit 0
    fi
}

# -----------------------------------------------------------------------------
# CDK destroy
# -----------------------------------------------------------------------------
destroy_cdk_stacks() {
    log_info "Destroying CDK stacks..."

    cd "${CDK_DIR}"

    # Activate virtual environment if it exists
    if [ -f "${PROJECT_ROOT}/.venv/bin/activate" ]; then
        source "${PROJECT_ROOT}/.venv/bin/activate"
    fi

    cdk destroy --all --force 2>&1 || {
        log_warn "CDK destroy encountered errors. Some resources may need manual cleanup."
    }

    log_info "CDK stacks destroyed."
}

# -----------------------------------------------------------------------------
# Delete ECR images
# -----------------------------------------------------------------------------
delete_ecr_images() {
    log_info "Cleaning up ECR repositories..."

    local repos
    repos=$(aws ecr describe-repositories \
        --query "repositories[?starts_with(repositoryName, 'agentcore-multi-tenant')].repositoryName" \
        --output text 2>/dev/null || echo "")

    if [ -z "$repos" ]; then
        log_info "No ECR repositories found to clean up."
        return
    fi

    for repo in $repos; do
        log_info "Deleting ECR repository: ${repo}"

        # Delete all images first
        local images
        images=$(aws ecr list-images --repository-name "$repo" \
            --query "imageIds[*]" --output json 2>/dev/null || echo "[]")

        if [ "$images" != "[]" ] && [ -n "$images" ]; then
            aws ecr batch-delete-image \
                --repository-name "$repo" \
                --image-ids "$images" 2>/dev/null || true
        fi

        # Delete the repository
        aws ecr delete-repository \
            --repository-name "$repo" \
            --force 2>/dev/null || {
            log_warn "Failed to delete ECR repository: ${repo}"
        }
    done

    log_info "ECR cleanup complete."
}

# -----------------------------------------------------------------------------
# Delete CloudWatch log groups
# -----------------------------------------------------------------------------
delete_log_groups() {
    log_info "Cleaning up CloudWatch log groups..."

    local prefixes=(
        "/aws/lambda/agentcore-multi-tenant"
        "/aws/bedrock/agentcore"
        "/aws/rds/cluster/agentcore-multi-tenant"
    )

    for prefix in "${prefixes[@]}"; do
        local groups
        groups=$(aws logs describe-log-groups \
            --log-group-name-prefix "$prefix" \
            --query "logGroups[*].logGroupName" \
            --output text 2>/dev/null || echo "")

        if [ -z "$groups" ]; then
            continue
        fi

        for group in $groups; do
            log_info "Deleting log group: ${group}"
            aws logs delete-log-group --log-group-name "$group" 2>/dev/null || {
                log_warn "Failed to delete log group: ${group}"
            }
        done
    done

    log_info "CloudWatch cleanup complete."
}

# -----------------------------------------------------------------------------
# Deregister AgentCore Runtime agents
# -----------------------------------------------------------------------------
deregister_agents() {
    log_info "Deregistering AgentCore Runtime agents..."

    # List agent runtimes and filter by naming convention
    local agents
    agents=$(aws bedrock list-agent-runtimes \
        --query "agentRuntimeSummaries[?starts_with(name, 'agentcore-multi-tenant')].agentRuntimeId" \
        --output text 2>/dev/null || echo "")

    if [ -z "$agents" ]; then
        log_info "No AgentCore Runtime agents found to deregister."
        return
    fi

    for agent_id in $agents; do
        log_info "Deregistering agent: ${agent_id}"
        aws bedrock delete-agent-runtime \
            --agent-runtime-id "$agent_id" 2>/dev/null || {
            log_warn "Failed to deregister agent: ${agent_id}"
        }
    done

    log_info "Agent deregistration complete."
}

# -----------------------------------------------------------------------------
# Clean up local artifacts
# -----------------------------------------------------------------------------
clean_local() {
    log_info "Cleaning up local artifacts..."

    # Remove CDK outputs
    rm -f "${PROJECT_ROOT}/cdk-outputs.json"

    # Remove CDK context
    rm -f "${CDK_DIR}/cdk.context.json"

    # Remove Python cache
    find "${PROJECT_ROOT}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "${PROJECT_ROOT}" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find "${PROJECT_ROOT}" -name "*.pyc" -delete 2>/dev/null || true

    log_info "Local cleanup complete."
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    echo "============================================================"
    echo "  AgentCore Multi-Tenant Hands-on - Cleanup"
    echo "============================================================"

    confirm_cleanup

    echo ""
    deregister_agents
    destroy_cdk_stacks
    delete_ecr_images
    delete_log_groups
    clean_local

    echo ""
    echo "============================================================"
    log_info "Cleanup complete!"
    echo ""
    echo "  All AWS resources and local artifacts have been removed."
    echo "  If you encounter orphaned resources, check the AWS console"
    echo "  for any remaining items with the 'agentcore-multi-tenant' prefix."
    echo "============================================================"
}

main "$@"
