"""Quick test to verify the portfolio dashboard setup."""
import sys
import importlib.util

def check_module(module_name, package=None):
    """Check if a module can be imported."""
    try:
        if package:
            __import__(f"{package}.{module_name}")
        else:
            __import__(module_name)
        return True, "OK"
    except ImportError as e:
        return False, str(e)

def main():
    """Run setup verification."""
    print("Portfolio Dashboard - Setup Verification")
    print("=" * 50)

    # Check required packages
    required_packages = [
        'streamlit',
        'pandas',
        'numpy',
        'yfinance',
        'fredapi',
        'sqlalchemy',
        'plotly',
        'scipy',
        'dotenv'
    ]

    print("\n1. Checking Python packages...")
    all_ok = True
    for package in required_packages:
        pkg_name = 'python-dotenv' if package == 'dotenv' else package
        success, msg = check_module(package)
        status = "✓" if success else "✗"
        print(f"   {status} {pkg_name}")
        if not success:
            all_ok = False
            print(f"      Error: {msg}")

    # Check project modules
    print("\n2. Checking project modules...")
    project_modules = [
        ('config', 'settings'),
        ('models', 'database'),
        ('models', 'portfolio'),
        ('services', 'data_fetcher'),
        ('services', 'risk_metrics'),
        ('services', 'portfolio_calculator'),
        ('utils', 'csv_handler'),
        ('utils', 'helpers')
    ]

    for package, module in project_modules:
        success, msg = check_module(module, package)
        status = "✓" if success else "✗"
        print(f"   {status} {package}.{module}")
        if not success:
            all_ok = False
            print(f"      Error: {msg}")

    # Check environment
    print("\n3. Checking environment configuration...")
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv()

        fred_key = os.getenv('FRED_API_KEY')
        if fred_key:
            print("   ✓ FRED_API_KEY configured")
        else:
            print("   ! FRED_API_KEY not set (optional - macro indicators won't work)")
    except Exception as e:
        print(f"   ! Could not check environment: {e}")

    # Check database
    print("\n4. Checking database setup...")
    try:
        from models.database import init_db
        init_db()
        print("   ✓ Database initialized successfully")
    except Exception as e:
        print(f"   ✗ Database initialization failed: {e}")
        all_ok = False

    # Summary
    print("\n" + "=" * 50)
    if all_ok:
        print("✓ All checks passed! Ready to run:")
        print("  streamlit run app.py")
    else:
        print("✗ Some checks failed. Please install missing packages:")
        print("  pip install -r requirements.txt")

    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
