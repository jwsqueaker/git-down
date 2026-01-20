#!/bin/bash
# Quick Docker deployment script

set -e

echo "🐳 Portfolio Dashboard - Docker Deployment"
echo "=========================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "⚠️  Warning: docker-compose not found, using docker compose"
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found, creating from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your FRED_API_KEY"
    read -p "Press Enter to continue or Ctrl+C to exit..."
fi

# Create data directory if it doesn't exist
mkdir -p data

echo ""
echo "🔨 Building Docker image..."
docker build -t portfolio-dashboard .

echo ""
echo "🚀 Starting services..."
$COMPOSE_CMD up -d

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📊 Dashboard is running at: http://localhost:8501"
echo ""
echo "Useful commands:"
echo "  View logs:  $COMPOSE_CMD logs -f"
echo "  Stop:       $COMPOSE_CMD down"
echo "  Restart:    $COMPOSE_CMD restart"
echo "  Status:     $COMPOSE_CMD ps"
echo ""
