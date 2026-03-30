#!/bin/bash

# Quick setup script for end users who clone the repo
# This installs dependencies and validates the environment

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          GitPulse - Setup & Dependencies Check                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Install dependencies
echo "Installing dependencies..."

if command -v uv &> /dev/null; then
    echo -e "${BLUE}Using uv...${NC}"
    uv sync
    
    # uv creates .venv - provide activation instructions  
    if [[ -d ".venv" ]]; then
        echo ""
        echo -e "${YELLOW}Virtual environment created in ./.venv${NC}"
        echo "Activate it with:"
        echo -e "  ${BLUE}source .venv/bin/activate${NC}"
        echo ""
        exit 0
    fi
elif command -v pip &> /dev/null; then
    echo -e "${BLUE}Using pip...${NC}"
    pip install -e .
else
    echo -e "${RED}✗ Neither 'uv' nor 'pip' found${NC}"
    echo "Please install Python 3.12+ and try again"
    exit 1
fi

# Verify dependencies
echo ""
echo -e "${BLUE}Verifying installed packages...${NC}"

python3 << 'PYEOF'
import sys

packages = {
    "google.cloud.bigquery": "google-cloud-bigquery",
    "pandas": "pandas",
    "streamlit": "streamlit",
    "dbt": "dbt-core",
    "dotenv": "python-dotenv",
    "pyarrow": "pyarrow",
    "requests": "requests",
    "tqdm": "tqdm",
}

all_installed = True
for import_name, package_name in packages.items():
    try:
        __import__(import_name)
        print(f"\033[0;32m✓\033[0m {package_name}")
    except ImportError:
        print(f"\033[0;31m✗\033[0m {package_name}")
        all_installed = False

sys.exit(0 if all_installed else 1)
PYEOF

if [[ $? -ne 0 ]]; then
    echo ""
    echo -e "${RED}Some dependencies missing - this is OK if using uv${NC}"
    echo "If you activated .venv, the packages are installed there."
fi

# Check configuration files
echo ""
echo -e "${BLUE}Checking environment setup...${NC}"

if [[ ! -f "$HOME/.env" ]]; then
    echo -e "${RED}✗${NC} Missing: ~/.env"
    echo "  → Create it with your GCP credentials:"
    echo "  "
    echo "  ${BLUE}cat > ~/.env << EOF"
    echo "  GCP_PROJECT_ID=your-project-id"
    echo "  GCS_BUCKET_NAME=your-bucket-name"
    echo "  BQ_DATASET_NAME=github_archive"
    echo "  GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json"
    echo "  EOF${NC}"
else
    echo -e "${GREEN}✓${NC} ~/.env found"
fi

if [[ ! -f "${SCRIPT_DIR}/dbt/profiles.yml" ]]; then
    echo -e "${RED}✗${NC} Missing: dbt/profiles.yml"
    echo "  → Configure your BigQuery connection there"
else
    echo -e "${GREEN}✓${NC} dbt/profiles.yml"
fi

echo ""
echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Create ~/.env with your GCP credentials (if not already done)"
echo "2. For uv users: activate the virtual environment first"
echo -e "   ${BLUE}source .venv/bin/activate${NC}"
echo "3. Then run the pipeline:"
echo -e "   ${BLUE}./run_pipeline.sh${NC}"
echo ""
