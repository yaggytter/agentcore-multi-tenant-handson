#!/bin/bash
# =============================================================================
# Setup Script for AgentCore Multi-Tenant Hands-on
# =============================================================================
# Checks prerequisites, creates a Python virtual environment, installs
# dependencies, and bootstraps the CDK environment.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# -----------------------------------------------------------------------------
# Check prerequisites
# -----------------------------------------------------------------------------
check_prerequisites() {
    log_info "Checking prerequisites..."

    local missing=0

    # Python 3.9+
    if command -v python3 &>/dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        log_info "Python: ${PYTHON_VERSION}"
    else
        log_error "Python 3 is not installed. Please install Python 3.9+."
        missing=1
    fi

    # Node.js 18+
    if command -v node &>/dev/null; then
        NODE_VERSION=$(node --version)
        log_info "Node.js: ${NODE_VERSION}"
    else
        log_error "Node.js is not installed. Please install Node.js 18+."
        missing=1
    fi

    # AWS CDK
    if command -v cdk &>/dev/null; then
        CDK_VERSION=$(cdk --version 2>&1 | head -1)
        log_info "CDK: ${CDK_VERSION}"
    else
        log_error "AWS CDK is not installed. Install with: npm install -g aws-cdk"
        missing=1
    fi

    # Docker
    if command -v docker &>/dev/null; then
        DOCKER_VERSION=$(docker --version)
        log_info "Docker: ${DOCKER_VERSION}"
        if ! docker info &>/dev/null; then
            log_warn "Docker daemon is not running. Please start Docker."
            missing=1
        fi
    else
        log_error "Docker is not installed. Please install Docker."
        missing=1
    fi

    # AWS CLI
    if command -v aws &>/dev/null; then
        AWS_VERSION=$(aws --version 2>&1)
        log_info "AWS CLI: ${AWS_VERSION}"
    else
        log_error "AWS CLI is not installed. Please install AWS CLI v2."
        missing=1
    fi

    # Check AWS credentials
    if aws sts get-caller-identity &>/dev/null; then
        AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
        AWS_REGION=$(aws configure get region 2>/dev/null || echo "not set")
        log_info "AWS Account: ${AWS_ACCOUNT}"
        log_info "AWS Region: ${AWS_REGION}"
    else
        log_error "AWS credentials are not configured. Run: aws configure"
        missing=1
    fi

    if [ "$missing" -ne 0 ]; then
        log_error "One or more prerequisites are missing. Please install them and try again."
        exit 1
    fi

    log_info "All prerequisites satisfied."
}

# -----------------------------------------------------------------------------
# Create Python virtual environment
# -----------------------------------------------------------------------------
setup_venv() {
    log_info "Setting up Python virtual environment..."

    cd "${PROJECT_ROOT}"

    if [ -d ".venv" ]; then
        log_warn "Virtual environment already exists. Skipping creation."
    else
        python3 -m venv .venv
        log_info "Virtual environment created at ${PROJECT_ROOT}/.venv"
    fi

    source .venv/bin/activate
    log_info "Virtual environment activated."

    # Upgrade pip
    pip install --upgrade pip --quiet
}

# -----------------------------------------------------------------------------
# Install dependencies
# -----------------------------------------------------------------------------
install_dependencies() {
    log_info "Installing Python dependencies..."

    cd "${PROJECT_ROOT}"
    source .venv/bin/activate

    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --quiet
        log_info "Python dependencies installed from requirements.txt."
    else
        log_warn "requirements.txt not found. Installing common dependencies..."
        pip install \
            aws-cdk-lib \
            constructs \
            boto3 \
            pytest \
            requests \
            --quiet
        log_info "Common dependencies installed."
    fi

    # Install CDK dependencies if cdk directory exists
    if [ -d "${PROJECT_ROOT}/cdk" ] && [ -f "${PROJECT_ROOT}/cdk/requirements.txt" ]; then
        pip install -r "${PROJECT_ROOT}/cdk/requirements.txt" --quiet
        log_info "CDK dependencies installed."
    fi
}

# -----------------------------------------------------------------------------
# CDK bootstrap
# -----------------------------------------------------------------------------
cdk_bootstrap() {
    log_info "Bootstrapping CDK..."

    cd "${PROJECT_ROOT}/cdk"

    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")

    cdk bootstrap "aws://${AWS_ACCOUNT}/${AWS_REGION}"

    log_info "CDK bootstrap complete for account ${AWS_ACCOUNT} in region ${AWS_REGION}."
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    echo "============================================================"
    echo "  AgentCore Multi-Tenant Hands-on - Setup"
    echo "============================================================"
    echo ""

    check_prerequisites
    setup_venv
    install_dependencies
    cdk_bootstrap

    echo ""
    echo "============================================================"
    log_info "Setup complete!"
    echo ""
    echo "  Next steps:"
    echo "    1. Activate the virtual environment:"
    echo "       source .venv/bin/activate"
    echo ""
    echo "    2. Deploy infrastructure (start with Chapter 1):"
    echo "       ./scripts/deploy.sh 1"
    echo "============================================================"
}

main "$@"
