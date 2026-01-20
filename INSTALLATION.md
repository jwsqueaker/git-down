# Installation Guide

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git
- Internet connection (for fetching market data)

## Step-by-Step Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd git-down
```

### 2. Create Virtual Environment (Recommended)

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Or use the automated setup script:
```bash
chmod +x setup.sh
./setup.sh
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` file and add your FRED API key:
```
FRED_API_KEY=your_api_key_here
```

**Get a free FRED API key:**
1. Go to https://fred.stlouisfed.org/
2. Create a free account
3. Visit https://fred.stlouisfed.org/docs/api/api_key.html
4. Request your API key
5. Copy it to the `.env` file

### 5. Verify Installation

Run the verification script:
```bash
python test_setup.py
```

This will check:
- All required packages are installed
- Project modules load correctly
- Environment is configured
- Database can be initialized

### 6. Run the Dashboard

```bash
streamlit run app.py
```

The dashboard will open automatically in your default browser at:
```
http://localhost:8501
```

## Troubleshooting

### ImportError: No module named 'X'

**Solution:** Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### FRED API errors

**Symptoms:** "Unable to fetch macro indicators" or "FRED API key not configured"

**Solution:**
1. Verify you have a FRED API key
2. Check it's correctly added to `.env` file
3. Ensure `.env` file is in the project root directory
4. Restart the Streamlit app

### Database errors

**Solution:** Delete the database file and restart:
```bash
rm portfolio.db
streamlit run app.py
```

### Port already in use

**Symptoms:** "Address already in use" error

**Solution:** Use a different port:
```bash
streamlit run app.py --server.port 8502
```

### yfinance data fetch errors

**Symptoms:** "No data found" or "Failed to get data"

**Possible causes:**
- Invalid ticker symbol
- Stock is delisted
- Network connectivity issues
- Yahoo Finance API is down

**Solution:**
- Verify ticker symbols are correct
- Check internet connection
- Try again later if Yahoo Finance is experiencing issues

### Slow performance

**Solutions:**
- Reduce the date range for historical data
- Limit the number of positions in your portfolio
- Close other browser tabs
- Use a more powerful machine

## Platform-Specific Notes

### macOS

If you encounter SSL certificate errors:
```bash
/Applications/Python\ 3.x/Install\ Certificates.command
```

### Windows

If you have issues with dependencies:
1. Install Microsoft Visual C++ Build Tools
2. Or use Anaconda distribution instead:
   ```bash
   conda create -n portfolio python=3.10
   conda activate portfolio
   pip install -r requirements.txt
   ```

### Linux

Install required system packages:
```bash
# Debian/Ubuntu
sudo apt-get update
sudo apt-get install python3-pip python3-venv

# Fedora/RHEL
sudo dnf install python3-pip python3-virtualenv
```

## Optional: Docker Installation

Coming soon - Docker support for containerized deployment.

## Updating

To update to the latest version:

```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

## Uninstallation

To completely remove:

```bash
# Deactivate virtual environment
deactivate

# Remove project directory
cd ..
rm -rf git-down

# Or just remove the virtual environment
rm -rf venv
```

## Getting Help

If you encounter issues:

1. Check this installation guide
2. Review the USAGE_GUIDE.md
3. Verify all prerequisites are met
4. Check Python version: `python --version` (should be 3.8+)
5. Verify pip is working: `pip --version`
6. Run the test script: `python test_setup.py`

## System Requirements

**Minimum:**
- CPU: 1 GHz dual-core
- RAM: 2 GB
- Disk: 500 MB free space
- Network: Broadband internet

**Recommended:**
- CPU: 2 GHz quad-core
- RAM: 4 GB or more
- Disk: 1 GB free space
- Network: Reliable high-speed internet

## Next Steps

After installation:

1. Review the USAGE_GUIDE.md for feature documentation
2. Upload a sample portfolio using `sample_data/portfolio_example.csv`
3. Explore the dashboard tabs
4. Configure your actual portfolio
5. Set up macro indicator tracking

Enjoy analyzing your portfolio!
