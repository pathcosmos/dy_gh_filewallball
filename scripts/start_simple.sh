#!/bin/bash

# FileWallBall API Simple Startup Script
# ======================================

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting FileWallBall API (Simple Version)...${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${BLUE}📝 Creating .env from template...${NC}"
    cp .env.simple .env
fi

# Check if uploads directory exists
if [ ! -d "uploads" ]; then
    echo -e "${BLUE}📁 Creating uploads directory...${NC}"
    mkdir -p uploads
    chmod 755 uploads
fi

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}📦 Installing dependencies...${NC}"
    if command -v uv &> /dev/null; then
        uv sync
    else
        pip install -r requirements_simple.txt
    fi
fi

# Run database migrations
echo -e "${BLUE}🗄️ Running database migrations...${NC}"
if command -v uv &> /dev/null; then
    uv run alembic upgrade head
else
    alembic upgrade head
fi

# Start the application
echo -e "${GREEN}✅ Starting FileWallBall API on http://localhost:8000${NC}"
echo -e "${GREEN}📚 API Documentation: http://localhost:8000/docs${NC}"
echo -e "${GREEN}❤️ Health Check: http://localhost:8000/health${NC}"

if command -v uv &> /dev/null; then
    uv run uvicorn app.main_simple:app --host 0.0.0.0 --port 8000 --reload
else
    uvicorn app.main_simple:app --host 0.0.0.0 --port 8000 --reload
fi