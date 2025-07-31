#!/bin/bash

# FileWallBall Development Script with uv
# Usage: ./scripts/dev.sh [command]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if uv is installed
check_uv() {
    if ! command -v uv &> /dev/null; then
        print_error "uv is not installed. Please install it first:"
        echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
}

# Install dependencies
install() {
    print_status "Installing dependencies with uv..."
    uv sync
    print_success "Dependencies installed successfully!"
}

# Install development dependencies
install_dev() {
    print_status "Installing development dependencies with uv..."
    uv sync --dev
    print_success "Development dependencies installed successfully!"
}

# Run the application
run() {
    print_status "Starting the application..."
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

# Run tests
test() {
    print_status "Running tests..."
    uv run pytest tests/ -v
}

# Run tests with coverage
test_coverage() {
    print_status "Running tests with coverage..."
    uv run pytest tests/ --cov=app --cov-report=html --cov-report=term
}

# Format code
format() {
    print_status "Formatting code with black..."
    uv run black app/ tests/
    print_status "Sorting imports with isort..."
    uv run isort app/ tests/
    print_success "Code formatting completed!"
}

# Lint code
lint() {
    print_status "Running flake8 linter..."
    uv run flake8 app/ tests/
    print_status "Running mypy type checker..."
    uv run mypy app/
    print_success "Linting completed!"
}

# Clean up
clean() {
    print_status "Cleaning up..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    find . -type f -name "*.pyd" -delete 2>/dev/null || true
    rm -rf .pytest_cache/ 2>/dev/null || true
    rm -rf htmlcov/ 2>/dev/null || true
    rm -rf .coverage 2>/dev/null || true
    print_success "Cleanup completed!"
}

# Show help
help() {
    echo "FileWallBall Development Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install      Install dependencies"
    echo "  install-dev  Install development dependencies"
    echo "  run          Run the application"
    echo "  test         Run tests"
    echo "  test-cov     Run tests with coverage"
    echo "  format       Format code with black and isort"
    echo "  lint         Run linters (flake8, mypy)"
    echo "  clean        Clean up cache files"
    echo "  help         Show this help message"
    echo ""
}

# Main script logic
main() {
    check_uv

    case "${1:-help}" in
        install)
            install
            ;;
        install-dev)
            install_dev
            ;;
        run)
            run
            ;;
        test)
            test
            ;;
        test-cov)
            test_coverage
            ;;
        format)
            format
            ;;
        lint)
            lint
            ;;
        clean)
            clean
            ;;
        help|--help|-h)
            help
            ;;
        *)
            print_error "Unknown command: $1"
            help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
