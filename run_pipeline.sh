#!/bin/bash

################################################################################
# GitPulse Automated Workflow Pipeline
# 
# Usage: ./run_pipeline.sh [OPTIONS]
#   -s, --start-date START_DATE     Start date in YYYYMMDD format (default: 7 days ago)
#   -e, --end-date END_DATE         End date in YYYYMMDD format (default: today)
#   -d, --dashboard                 Launch Streamlit dashboard after pipeline completes
#   -h, --help                      Show this help message
#
# Examples:
#   ./run_pipeline.sh                                          # Uses defaults
#   ./run_pipeline.sh -s 20240101 -e 20240131                # Custom date range
#   ./run_pipeline.sh -s 20240101 -e 20240131 -d             # With dashboard
#
################################################################################

set -o pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/.logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/gitpulse_${TIMESTAMP}.log"

# Defaults
DAYS_BACK=7
END_DATE=$(date +%Y%m%d)
START_DATE=$(date -d "${DAYS_BACK} days ago" +%Y%m%d)
LAUNCH_DASHBOARD=false

# Parse command-line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--start-date)
                START_DATE="$2"
                shift 2
                ;;
            -e|--end-date)
                END_DATE="$2"
                shift 2
                ;;
            -d|--dashboard)
                LAUNCH_DASHBOARD=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
}

# Display help message
show_help() {
    head -n 15 "$0" | tail -n 13
}

# Initialize logging
init_logging() {
    mkdir -p "${LOG_DIR}"
    touch "${LOG_FILE}"
    echo "Pipeline started at $(date)" > "${LOG_FILE}"
}

# Log message with timestamp
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

# Load environment variables from ~/.env or ./.env
load_env_vars() {
    local env_file
    
    # Check home directory first, then project directory
    if [[ -f "$HOME/.env" ]]; then
        env_file="$HOME/.env"
    elif [[ -f "${SCRIPT_DIR}/.env" ]]; then
        env_file="${SCRIPT_DIR}/.env"
    else
        log "ERROR" "Missing .env file"
        log "ERROR" "Please create either ~/.env or ./.env with your GCP credentials:"
        log "ERROR" "  GCP_PROJECT_ID=your-project-id"
        log "ERROR" "  GCS_BUCKET_NAME=your-bucket-name"
        log "ERROR" "  BQ_DATASET_NAME=github_archive"
        log "ERROR" "  GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json"
        exit 1
    fi
    
    # Load environment variables from .env file
    # Handle format: KEY=value or KEY = "value"
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        
        # Trim whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        
        # Remove quotes if present
        value="${value%\"}"
        value="${value#\"}"
        
        export "$key"="$value"
    done < "$env_file"
    
    log "INFO" "Environment variables loaded from $env_file"
}

# Validate date format
validate_date_format() {
    local date=$1
    local date_name=$2
    
    if ! [[ "$date" =~ ^[0-9]{8}$ ]]; then
        log "ERROR" "${date_name} must be in YYYYMMDD format (got: $date)"
        exit 1
    fi
    
    # Validate it's an actual date
    if ! date -d "${date:0:4}-${date:4:2}-${date:6:2}" >/dev/null 2>&1; then
        log "ERROR" "Invalid ${date_name}: $date is not a valid date"
        exit 1
    fi
}

# Check if all required environment variables and files exist
check_prerequisites() {
    log "INFO" "Checking prerequisites..."
    
    # Check if profiles.yml exists for dbt
    if [[ ! -f "${SCRIPT_DIR}/dbt/profiles.yml" ]]; then
        log "ERROR" "Missing dbt/profiles.yml file"
        log "ERROR" "Please configure your BigQuery connection in dbt/profiles.yml"
        exit 1
    fi
    
    # Check if required Python scripts exist
    if [[ ! -f "${SCRIPT_DIR}/ingestion/ingest.py" ]]; then
        log "ERROR" "Missing ingestion/ingest.py"
        exit 1
    fi
    
    # Check if dependencies are installed
    if ! python3 -c "import google.cloud.bigquery; import pandas; import dbt" 2>/dev/null; then
        log "ERROR" "Required dependencies not installed"
        log "ERROR" "Please run: pip install -e . or uv sync"
        exit 1
    fi
    
    log "INFO" "Prerequisites check passed ✓"
}

# Verify Python environment is ready
verify_environment() {
    log "INFO" "Verifying Python environment..."
    
    # Check Python version
    local python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log "INFO" "Python version: $python_version"
    
    # Check key packages
    local packages=("google.cloud.bigquery" "pandas" "dbt.core" "streamlit")
    for package in "${packages[@]}"; do
        if python3 -c "import ${package%.*}" 2>/dev/null; then
            log "INFO" "✓ ${package} installed"
        else
            log "ERROR" "✗ ${package} not installed"
            exit 1
        fi
    done
    
    log "INFO" "Environment verification complete ✓"
}

# Run ingestion pipeline
run_ingestion() {
    log "INFO" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "INFO" "STAGE 1: DATA INGESTION"
    log "INFO" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "INFO" "Fetching GitHub Archive data from ${START_DATE} to ${END_DATE}..."
    
    if python3 "${SCRIPT_DIR}/ingestion/ingest.py" 2>&1 | tee -a "${LOG_FILE}"; then
        log "INFO" "Data ingestion completed successfully ✓"
        return 0
    else
        log "ERROR" "Data ingestion failed ✗"
        return 1
    fi
}

# Run dbt transformations
run_dbt_transformations() {
    log "INFO" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "INFO" "STAGE 2: DATA TRANSFORMATION (dbt)"
    log "INFO" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    cd "${SCRIPT_DIR}/dbt" || exit 1
    
    log "INFO" "Running dbt run..."
    if dbt run --profiles-dir . 2>&1 | tee -a "${LOG_FILE}"; then
        log "INFO" "dbt transformations completed successfully ✓"
        
        log "INFO" "Running dbt tests..."
        if dbt test --profiles-dir . 2>&1 | tee -a "${LOG_FILE}"; then
            log "INFO" "dbt tests passed ✓"
            return 0
        else
            log "WARN" "Some dbt tests failed, but continuing..."
            return 0
        fi
    else
        log "ERROR" "dbt transformations failed ✗"
        return 1
    fi
}

# Launch Streamlit dashboard
launch_dashboard() {
    log "INFO" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log "INFO" "STAGE 3: LAUNCHING DASHBOARD"
    log "INFO" "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    cd "${SCRIPT_DIR}/dashboard" || exit 1
    
    log "INFO" "Starting Streamlit dashboard..."
    log "INFO" "Dashboard will be available at http://localhost:8501"
    
    streamlit run streamlit_dashboard.py 2>&1 | tee -a "${LOG_FILE}"
}

# Print summary
print_summary() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}PIPELINE EXECUTION SUMMARY${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "Date Range:        ${YELLOW}${START_DATE} to ${END_DATE}${NC}"
    echo -e "Log File:          ${YELLOW}${LOG_FILE}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Main execution
main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║          GitPulse Automated Workflow Pipeline                  ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Check if .venv exists but not activated
    if [[ -d "${SCRIPT_DIR}/.venv" ]] && [[ -z "$VIRTUAL_ENV" ]]; then
        log "WARN" "Virtual environment found but not activated"
        log "WARN" "Please activate it first:"
        log "WARN" "  source .venv/bin/activate"
        exit 1
    fi
    
    # Parse arguments
    parse_arguments "$@"
    
    # Validate inputs
    validate_date_format "$START_DATE" "START_DATE"
    validate_date_format "$END_DATE" "END_DATE"
    
    if [[ "$START_DATE" > "$END_DATE" ]]; then
        log "ERROR" "START_DATE ($START_DATE) cannot be after END_DATE ($END_DATE)"
        exit 1
    fi
    
    # Initialize
    init_logging
    log "INFO" "Pipeline Configuration:"
    log "INFO" "  Start Date: ${START_DATE}"
    log "INFO" "  End Date: ${END_DATE}"
    log "INFO" "  Dashboard: ${LAUNCH_DASHBOARD}"
    log "INFO" "  Log File: ${LOG_FILE}"
    
    # Execute pipeline
    check_prerequisites || exit 1
    verify_environment || exit 1
    load_env_vars || exit 1
    
    # Export environment variables for ingestion
    export START_DATE
    export END_DATE
    
    # Run pipeline stages
    if run_ingestion && run_dbt_transformations; then
        echo -e "${GREEN}"
        echo "╔════════════════════════════════════════════════════════════════╗"
        echo "║                  ✓ PIPELINE COMPLETED SUCCESSFULLY             ║"
        echo "╚════════════════════════════════════════════════════════════════╝"
        echo -e "${NC}"
        
        print_summary
        log "INFO" "Pipeline completed successfully!"
        
        # Launch dashboard if requested
        if [[ "$LAUNCH_DASHBOARD" == true ]]; then
            launch_dashboard
        fi
        
        exit 0
    else
        echo -e "${RED}"
        echo "╔════════════════════════════════════════════════════════════════╗"
        echo "║                    ✗ PIPELINE FAILED                          ║"
        echo "╚════════════════════════════════════════════════════════════════╝"
        echo -e "${NC}"
        
        log "ERROR" "Pipeline failed. Check log file for details: ${LOG_FILE}"
        print_summary
        exit 1
    fi
}

# Error handling
trap 'log "ERROR" "Script interrupted"; exit 130' INT TERM

# Run main function
main "$@"
