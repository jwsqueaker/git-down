#!/bin/bash
# Docker Quick Start Guide for Portfolio Dashboard

echo "╔════════════════════════════════════════════════════════╗"
echo "║   Portfolio Dashboard - Docker Quick Start            ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check Docker installation
echo "Step 1: Checking Docker installation..."
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker is installed: $(docker --version)"
else
    echo -e "${RED}✗${NC} Docker is not installed"
    echo ""
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    echo ""
    echo "Installation commands by platform:"
    echo "  macOS:   Download Docker Desktop from docker.com"
    echo "  Windows: Download Docker Desktop from docker.com"
    echo "  Ubuntu:  sudo apt-get update && sudo apt-get install docker.io"
    echo "  Fedora:  sudo dnf install docker"
    echo ""
    exit 1
fi

# Check Docker is running
if docker info &> /dev/null; then
    echo -e "${GREEN}✓${NC} Docker daemon is running"
else
    echo -e "${RED}✗${NC} Docker daemon is not running"
    echo "Please start Docker Desktop or run: sudo systemctl start docker"
    exit 1
fi

# Step 2: Check for .env file
echo ""
echo "Step 2: Checking environment configuration..."
if [ -f .env ]; then
    echo -e "${GREEN}✓${NC} .env file found"

    # Check if FRED_API_KEY is set
    if grep -q "FRED_API_KEY=" .env && ! grep -q "FRED_API_KEY=your_" .env; then
        echo -e "${GREEN}✓${NC} FRED_API_KEY is configured"
    else
        echo -e "${YELLOW}⚠${NC}  FRED_API_KEY not set or using default value"
        echo "   Macro indicators won't work without a valid FRED API key"
        echo "   Get one free at: https://fred.stlouisfed.org/docs/api/api_key.html"
    fi
else
    echo -e "${YELLOW}⚠${NC}  No .env file found, creating from example..."
    cp .env.example .env
    echo "   Please edit .env and add your FRED_API_KEY"
fi

# Step 3: Create data directory
echo ""
echo "Step 3: Setting up data directory..."
if [ ! -d data ]; then
    mkdir -p data
    echo -e "${GREEN}✓${NC} Created data directory for persistent storage"
else
    echo -e "${GREEN}✓${NC} Data directory exists"
fi

# Step 4: Build Docker image
echo ""
echo "Step 4: Building Docker image..."
echo "This may take a few minutes on first run..."
if docker build -t portfolio-dashboard . ; then
    echo -e "${GREEN}✓${NC} Docker image built successfully"
else
    echo -e "${RED}✗${NC} Failed to build Docker image"
    exit 1
fi

# Step 5: Stop any existing container
echo ""
echo "Step 5: Checking for existing containers..."
if docker ps -a | grep -q portfolio-dashboard; then
    echo "Stopping and removing existing container..."
    docker stop portfolio-dashboard 2>/dev/null
    docker rm portfolio-dashboard 2>/dev/null
    echo -e "${GREEN}✓${NC} Cleaned up existing container"
fi

# Step 6: Run the container
echo ""
echo "Step 6: Starting Portfolio Dashboard..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

docker run -d \
    --name portfolio-dashboard \
    -p 8501:8501 \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/sample_data:/app/sample_data" \
    -e FRED_API_KEY="${FRED_API_KEY}" \
    --restart unless-stopped \
    portfolio-dashboard

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Container started successfully"
else
    echo -e "${RED}✗${NC} Failed to start container"
    exit 1
fi

# Step 7: Wait for application to be ready
echo ""
echo "Step 7: Waiting for application to start..."
sleep 5

# Check if container is running
if docker ps | grep -q portfolio-dashboard; then
    echo -e "${GREEN}✓${NC} Container is running"
else
    echo -e "${RED}✗${NC} Container failed to start. Checking logs..."
    docker logs portfolio-dashboard
    exit 1
fi

# Step 8: Show status and access info
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║              🎉 SUCCESS! Dashboard is running          ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Dashboard URL:${NC} http://localhost:8501"
echo ""
echo "Quick Commands:"
echo "  View logs:      docker logs -f portfolio-dashboard"
echo "  Stop:           docker stop portfolio-dashboard"
echo "  Start:          docker start portfolio-dashboard"
echo "  Restart:        docker restart portfolio-dashboard"
echo "  Remove:         docker stop portfolio-dashboard && docker rm portfolio-dashboard"
echo ""
echo "Next Steps:"
echo "  1. Open http://localhost:8501 in your browser"
echo "  2. Upload a portfolio CSV from the sidebar"
echo "  3. Use sample_data/portfolio_example.csv to test"
echo ""
echo "Container Info:"
docker ps --filter name=portfolio-dashboard --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Try to open browser (macOS/Linux)
if command -v open &> /dev/null; then
    echo "Opening browser..."
    open http://localhost:8501
elif command -v xdg-open &> /dev/null; then
    echo "Opening browser..."
    xdg-open http://localhost:8501
else
    echo "Please open http://localhost:8501 in your browser"
fi
