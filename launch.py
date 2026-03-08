#!/usr/bin/env python3
"""
Simple launcher for the Pothole Detection Streamlit app.
Works on all platforms (Windows, macOS, Linux).
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    print("=" * 50)
    print("🛣️  LA Pothole Detection - Launcher")
    print("=" * 50)
    print()

    # Check if streamlit is installed
    try:
        import streamlit
        print(f"✅ Streamlit {streamlit.__version__} found")
    except ImportError:
        print("❌ Streamlit not installed")
        print()
        print("Installing dependencies...")
        print("This may take a few minutes...")
        print()

        # Install requirements
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])

        print()
        print("✅ Dependencies installed!")

    # Check if .env exists, create if not
    env_file = Path(".env")
    if not env_file.exists():
        print()
        print("📝 Creating .env configuration file...")
        env_file.write_text("""# Planet API Configuration (optional)
PL_API_KEY=your_planet_api_key_here
PL_SERIES_NAME=PlanetScope Weekly Basemap

# AWS Configuration (optional)
# AWS_BUCKET=your-bucket-name
# AWS_PREFIX=pothole-data/
# AWS_REGION=us-west-2
""")
        print("✅ .env file created - edit with your credentials if needed")

    # Launch Streamlit
    print()
    print("=" * 50)
    print("🚀 Launching Streamlit app...")
    print()
    print("The app will open at: http://localhost:8501")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    print()

    # Run streamlit
    subprocess.call([
        sys.executable, "-m", "streamlit", "run", "streamlit_app.py"
    ])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Python 3.9+ is installed")
        print("2. Install GDAL system package if needed")
        print("3. Check requirements.txt exists")
        sys.exit(1)
