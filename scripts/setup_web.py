"""
LAHSO Web Application Setup Script
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from lahso.paths import (
    Q_TABLES_DIR,
    RAW_DATA_DIR,
    SHIPMENT_LOGS_DIR,
    SIMULATION_OUTPUTS_DIR,
    TRAINING_METRICS_DIR,
    WEB_TEMPLATES_DIR,
    ensure_directories,
)

def main():
    print("🔧 Setting up LAHSO Web Application...")
    
    # Create required directories
    directories = [
        WEB_TEMPLATES_DIR,
        Q_TABLES_DIR,
        TRAINING_METRICS_DIR,
        SIMULATION_OUTPUTS_DIR,
        SHIPMENT_LOGS_DIR,
    ]
    
    ensure_directories(*directories)
    for directory in directories:
        print(f"✓ Created directory: {directory}")
    
    # Check if templates/index.html exists
    if not (WEB_TEMPLATES_DIR / "index.html").exists():
        print("❌ templates/index.html not found!")
        print("Please copy the HTML content to templates/index.html")
    else:
        print("✓ templates/index.html found")
    
    # Check if raw data exists
    if not RAW_DATA_DIR.exists():
        print("⚠️  data/raw directory not found")
        print("Please copy your LAHSO datasets into the data/raw/ folders")
    else:
        print("✓ data/raw directory found")
    
    print("\n📋 Setup complete! Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Install and configure Gurobi")
    print("3. Copy HTML content to templates/index.html")
    print("4. Ensure data/raw/ contains your LAHSO data")
    print("5. Run: python scripts/run_web.py")

if __name__ == '__main__':
    main()
