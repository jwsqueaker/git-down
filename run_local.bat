@echo off
REM Local Deployment Script for LA Pothole Detection (Windows)

echo ========================================
echo LA Pothole Detection - Local Deployment
echo ========================================
echo.

REM Check if in correct directory
if not exist "streamlit_app.py" (
    echo Error: streamlit_app.py not found
    echo Please run this from the git-down directory
    pause
    exit /b 1
)

REM Check Python
echo Checking Python version...
python --version
if errorlevel 1 (
    echo Error: Python not found
    echo Please install Python 3.9 or later
    pause
    exit /b 1
)

REM Create virtual environment
echo.
echo Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo.
echo Installing Python dependencies...
echo This may take a few minutes...
python -m pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo Error: Failed to install dependencies
    echo.
    echo You may need to install GDAL manually:
    echo 1. Download GDAL wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/
    echo 2. Install with: pip install GDAL-3.x.x-cpXX-cpXXm-win_amd64.whl
    echo 3. Then run this script again
    pause
    exit /b 1
)

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo.
    echo Creating .env file...
    (
        echo # Planet API Configuration (optional^)
        echo PL_API_KEY=your_planet_api_key_here
        echo PL_SERIES_NAME=PlanetScope Weekly Basemap
        echo.
        echo # AWS Configuration (optional^)
        echo # AWS_BUCKET=your-bucket-name
        echo # AWS_PREFIX=pothole-data/
        echo # AWS_REGION=us-west-2
    ) > .env
    echo .env file created - edit with your credentials if needed
)

REM Launch Streamlit
echo.
echo ========================================
echo Starting Streamlit app...
echo.
echo The app will open in your browser at:
echo http://localhost:8501
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

streamlit run streamlit_app.py

pause
