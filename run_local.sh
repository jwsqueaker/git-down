#!/bin/bash
# Local Deployment Script for LA Pothole Detection

echo "🚀 LA Pothole Detection - Local Deployment"
echo "=========================================="
echo ""

# Check if in git-down directory
if [ ! -f "streamlit_app.py" ]; then
    echo "❌ Error: streamlit_app.py not found"
    echo "Please run this from the git-down directory"
    exit 1
fi

# Check Python version
echo "📋 Checking Python version..."
python3 --version || { echo "❌ Python 3 not found"; exit 1; }

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install system dependencies info
echo ""
echo "📚 System Dependencies Required:"
echo "   If you haven't installed GDAL, run:"
echo "   Ubuntu/Debian: sudo apt-get install gdal-bin libgdal-dev"
echo "   macOS: brew install gdal"
echo ""
read -p "Press Enter to continue (or Ctrl+C to exit and install GDAL first)..."

# Install Python dependencies
echo ""
echo "📥 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    echo "Try installing GDAL system package first"
    exit 1
fi

echo ""
echo "✅ All dependencies installed!"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env file for configuration..."
    cat > .env << 'EOF'
# Planet API Configuration (optional)
PL_API_KEY=your_planet_api_key_here
PL_SERIES_NAME=PlanetScope Weekly Basemap

# AWS Configuration (optional)
# AWS_BUCKET=your-bucket-name
# AWS_PREFIX=pothole-data/
# AWS_REGION=us-west-2
EOF
    echo "✅ Created .env file - edit it with your credentials if needed"
fi

# Launch Streamlit
echo ""
echo "🎉 Starting Streamlit app..."
echo ""
echo "=========================================="
echo "The app will open in your browser at:"
echo "👉 http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

streamlit run streamlit_app.py
