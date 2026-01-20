#!/bin/bash

echo "================================================"
echo "Portfolio Dashboard - Setup Script"
echo "================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip."
    exit 1
fi

echo "✓ pip3 found"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Copy .env.example to .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your FRED API key"
else
    echo "✓ .env file already exists"
fi

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Get a free FRED API key:"
echo "   https://fred.stlouisfed.org/docs/api/api_key.html"
echo ""
echo "2. Add your API key to .env file:"
echo "   FRED_API_KEY=your_key_here"
echo ""
echo "3. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "4. Run the dashboard:"
echo "   streamlit run app.py"
echo ""
echo "5. Upload a portfolio CSV or use the sample:"
echo "   sample_data/portfolio_example.csv"
echo ""
echo "================================================"
