#!/bin/bash

# FileWallBall Installation Script
# Supports multiple installation methods: uv, pip, Docker, and Kubernetes

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

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Show help
show_help() {
    echo "FileWallBall Installation Script"
    echo ""
    echo "Usage: $0 [OPTIONS] [METHOD]"
    echo ""
    echo "OPTIONS:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --verbose  Enable verbose output"
    echo ""
    echo "METHODS:"
    echo "  uv             Install using uv (recommended)"
    echo "  pip            Install using pip"
    echo "  docker         Build and run with Docker"
    echo "  k8s            Deploy to Kubernetes"
    echo "  all            Install all methods"
    echo ""
    echo "EXAMPLES:"
    echo "  $0 uv          # Install with uv"
    echo "  $0 pip         # Install with pip"
    echo "  $0 docker      # Build and run Docker container"
    echo "  $0 k8s         # Deploy to Kubernetes"
    echo ""
}

# Install with uv
install_uv() {
    print_status "Installing FileWallBall with uv..."

    if ! command_exists uv; then
        print_status "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi

    print_status "Installing dependencies..."
    uv sync --dev

    print_success "FileWallBall installed successfully with uv!"
}

# Install with pip
install_pip() {
    print_status "Installing FileWallBall with pip..."

    if ! command_exists pip; then
        print_error "pip is not installed. Please install Python and pip first."
        exit 1
    fi

    print_status "Installing production dependencies..."
    pip install -r requirements.txt

    print_status "Installing development dependencies..."
    pip install -r requirements-dev.txt

    print_success "FileWallBall installed successfully with pip!"
}

# Install with setup.py
install_setup() {
    print_status "Installing FileWallBall with setup.py..."

    if ! command_exists pip; then
        print_error "pip is not installed. Please install Python and pip first."
        exit 1
    fi

    print_status "Installing in development mode..."
    pip install -e .[dev]

    print_success "FileWallBall installed successfully with setup.py!"
}

# Build and run with Docker
install_docker() {
    print_status "Building and running FileWallBall with Docker..."

    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    print_status "Building Docker image..."
    docker build -t filewallball:latest .

    print_status "Creating .env file from template..."
    if [ ! -f .env ]; then
        cp env.example .env
        print_warning "Please edit .env file with your configuration before running."
    fi

    print_success "Docker image built successfully!"
    echo ""
    echo "To run the container:"
    echo "  docker run -p 8000:8000 --env-file .env filewallball:latest"
    echo ""
}

# Deploy to Kubernetes
install_k8s() {
    print_status "Deploying FileWallBall to Kubernetes..."

    if ! command_exists kubectl; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi

    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    print_status "Building Docker image..."
    docker build -t filewallball:latest .

    print_status "Deploying to Kubernetes..."
    ./scripts/deploy.sh

    print_success "FileWallBall deployed to Kubernetes successfully!"
}

# Setup environment
setup_environment() {
    print_status "Setting up environment..."

    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        print_status "Creating .env file from template..."
        cp env.example .env
        print_warning "Please edit .env file with your configuration."
    fi

    # Create necessary directories
    print_status "Creating necessary directories..."
    mkdir -p uploads logs backups

    # Set permissions
    chmod 755 uploads
    chmod 755 logs
    chmod 755 backups

    print_success "Environment setup completed!"
}

# Verify installation
verify_installation() {
    print_status "Verifying installation..."

    # Check if Python can import the app
    if python -c "import app.main" 2>/dev/null; then
        print_success "Python import verification passed!"
    else
        print_error "Python import verification failed!"
        return 1
    fi

    # Check if required commands are available
    if command_exists uvicorn; then
        print_success "uvicorn is available!"
    else
        print_warning "uvicorn not found in PATH"
    fi

    print_success "Installation verification completed!"
}

# Main installation function
main() {
    local method=""
    local verbose=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            uv|pip|setup|docker|k8s|all)
                method="$1"
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Default to uv if no method specified
    if [ -z "$method" ]; then
        method="uv"
    fi

    # Set verbose mode
    if [ "$verbose" = true ]; then
        set -x
    fi

    print_status "Starting FileWallBall installation with method: $method"

    case $method in
        uv)
            install_uv
            setup_environment
            verify_installation
            ;;
        pip)
            install_pip
            setup_environment
            verify_installation
            ;;
        setup)
            install_setup
            setup_environment
            verify_installation
            ;;
        docker)
            install_docker
            ;;
        k8s)
            install_k8s
            ;;
        all)
            install_uv
            install_pip
            install_setup
            install_docker
            setup_environment
            verify_installation
            ;;
        *)
            print_error "Unknown installation method: $method"
            show_help
            exit 1
            ;;
    esac

    print_success "FileWallBall installation completed!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your configuration"
    echo "2. Run: ./scripts/dev.sh run"
    echo "3. Visit: http://localhost:8000/docs"
    echo ""
}

# Run main function with all arguments
main "$@"
