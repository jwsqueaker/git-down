#!/bin/bash
# Verify Docker setup without actually running Docker

echo "╔════════════════════════════════════════════════════════╗"
echo "║     Portfolio Dashboard - Docker Setup Verification   ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# Check required files
echo "Checking required files..."
echo ""

FILES=(
    "Dockerfile:Docker image definition"
    "docker-compose.yml:Docker Compose configuration"
    ".dockerignore:Docker build optimization"
    "requirements.txt:Python dependencies"
    "app.py:Main application"
    ".env.example:Environment template"
    "docker-quickstart.sh:Quick start script"
)

for item in "${FILES[@]}"; do
    FILE="${item%%:*}"
    DESC="${item##*:}"

    if [ -f "$FILE" ]; then
        echo -e "${GREEN}✓${NC} $FILE"
        echo "   └─ $DESC"
    else
        echo -e "${RED}✗${NC} $FILE - MISSING!"
        echo "   └─ $DESC"
        ((ERRORS++))
    fi
done

echo ""
echo "Checking deployment files..."
echo ""

DEPLOY_FILES=(
    "deployment/nginx.conf:Nginx reverse proxy config"
    "deployment/portfolio-dashboard.service:Systemd service"
    "deployment/deploy-docker.sh:Automated deployment script"
)

for item in "${DEPLOY_FILES[@]}"; do
    FILE="${item%%:*}"
    DESC="${item##*:}"

    if [ -f "$FILE" ]; then
        echo -e "${GREEN}✓${NC} $FILE"
    else
        echo -e "${RED}✗${NC} $FILE - MISSING!"
        ((ERRORS++))
    fi
done

echo ""
echo "Checking Python application files..."
echo ""

APP_DIRS=(
    "models:Database models"
    "services:Business logic"
    "utils:Utility functions"
    "config:Configuration"
)

for item in "${APP_DIRS[@]}"; do
    DIR="${item%%:*}"
    DESC="${item##*:}"

    if [ -d "$DIR" ]; then
        FILE_COUNT=$(find "$DIR" -name "*.py" | wc -l)
        echo -e "${GREEN}✓${NC} $DIR/ ($FILE_COUNT Python files)"
        echo "   └─ $DESC"
    else
        echo -e "${RED}✗${NC} $DIR/ - MISSING!"
        ((ERRORS++))
    fi
done

echo ""
echo "Checking documentation..."
echo ""

DOCS=(
    "README.md"
    "INSTALLATION.md"
    "USAGE_GUIDE.md"
    "DEPLOYMENT.md"
    "DOCKER_README.md"
    "FAQ.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo -e "${GREEN}✓${NC} $doc"
    else
        echo -e "${YELLOW}⚠${NC}  $doc - Not found"
    fi
done

echo ""
echo "Checking sample data..."
echo ""

if [ -d "sample_data" ]; then
    echo -e "${GREEN}✓${NC} sample_data/ directory exists"

    if [ -f "sample_data/portfolio_example.csv" ]; then
        echo -e "${GREEN}✓${NC} portfolio_example.csv"
    fi

    if [ -f "sample_data/ltcma_example.csv" ]; then
        echo -e "${GREEN}✓${NC} ltcma_example.csv"
    fi
else
    echo -e "${YELLOW}⚠${NC}  sample_data/ directory not found"
fi

echo ""
echo "Analyzing Dockerfile..."
echo ""

if [ -f "Dockerfile" ]; then
    # Check for security best practices
    if grep -q "HEALTHCHECK" Dockerfile; then
        echo -e "${GREEN}✓${NC} Health check configured"
    fi

    if grep -q "python:3" Dockerfile; then
        PYTHON_VERSION=$(grep "FROM python" Dockerfile | head -1 | cut -d: -f2 | cut -d- -f1)
        echo -e "${GREEN}✓${NC} Python version: $PYTHON_VERSION"
    fi

    if grep -q "EXPOSE" Dockerfile; then
        PORT=$(grep "EXPOSE" Dockerfile | awk '{print $2}')
        echo -e "${GREEN}✓${NC} Exposes port: $PORT"
    fi
fi

echo ""
echo "Analyzing docker-compose.yml..."
echo ""

if [ -f "docker-compose.yml" ]; then
    if grep -q "volumes:" docker-compose.yml; then
        echo -e "${GREEN}✓${NC} Volume mounting configured (data persistence)"
    fi

    if grep -q "restart:" docker-compose.yml; then
        RESTART=$(grep "restart:" docker-compose.yml | head -1 | awk '{print $2}')
        echo -e "${GREEN}✓${NC} Restart policy: $RESTART"
    fi

    if grep -q "environment:" docker-compose.yml; then
        echo -e "${GREEN}✓${NC} Environment variables configured"
    fi

    if grep -q "healthcheck:" docker-compose.yml; then
        echo -e "${GREEN}✓${NC} Health check enabled"
    fi
fi

echo ""
echo "Checking .env configuration..."
echo ""

if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} .env file exists"

    if grep -q "FRED_API_KEY" .env; then
        if grep -q "FRED_API_KEY=your_" .env || grep -q "FRED_API_KEY=$" .env; then
            echo -e "${YELLOW}⚠${NC}  FRED_API_KEY not configured (using default)"
            echo "   Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html"
        else
            echo -e "${GREEN}✓${NC} FRED_API_KEY configured"
        fi
    fi
else
    echo -e "${YELLOW}⚠${NC}  No .env file (will use .env.example defaults)"
    echo "   Run: cp .env.example .env"
fi

echo ""
echo "Checking executability..."
echo ""

SCRIPTS=(
    "docker-quickstart.sh"
    "setup.sh"
    "deployment/deploy-docker.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo -e "${GREEN}✓${NC} $script is executable"
        else
            echo -e "${YELLOW}⚠${NC}  $script not executable (run: chmod +x $script)"
        fi
    fi
done

echo ""
echo "Estimating Docker image size..."
echo ""

if [ -f "requirements.txt" ]; then
    PKG_COUNT=$(grep -v "^#" requirements.txt | grep -v "^$" | wc -l)
    echo "  - Base image (Python 3.10): ~150 MB"
    echo "  - Python packages ($PKG_COUNT total): ~200-300 MB"
    echo "  - Application code: ~5 MB"
    echo "  ─────────────────────────────────────"
    echo "  Estimated total: ~400-500 MB"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED!${NC}"
    echo ""
    echo "Your Docker setup is ready to deploy!"
    echo ""
    echo "Next steps:"
    echo "  1. Ensure Docker is installed and running"
    echo "  2. Configure .env file with FRED_API_KEY"
    echo "  3. Run: ./docker-quickstart.sh"
    echo "  4. Access at: http://localhost:8501"
    echo ""
else
    echo -e "${RED}✗ FOUND $ERRORS ERROR(S)${NC}"
    echo ""
    echo "Please fix the missing files before deploying."
    echo ""
fi

echo "Documentation:"
echo "  Quick Start:  ./docker-quickstart.sh"
echo "  Full Guide:   DOCKER_README.md"
echo "  General Help: README.md"
echo ""
