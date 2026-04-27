#!/usr/bin/env python3
"""
LAHSO Web Application - Production Runner
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

def check_requirements():
    """Check if all requirements are met"""
    try:
        import flask
        import flask_socketio
        import pandas
        import numpy
        import gurobipy
        import simpy
        print("✓ All Python dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def check_datasets():
    """Check if datasets are available"""
    datasets_path = RAW_DATA_DIR
    if not datasets_path.exists():
        print("❌ Data directory not found")
        print("Please copy your LAHSO datasets to the data/raw/ folders")
        return False
    
    required_files = [
        datasets_path / "network" / "Network.csv",
        datasets_path / "network" / "Network_Barge.csv",
        datasets_path / "network" / "Network_Train.csv",
        datasets_path / "network" / "Network_Truck.csv",
        datasets_path / "schedules" / "Fixed Vehicle Schedule.csv",
        datasets_path / "schedules" / "Truck Schedule.csv",
        datasets_path / "costs" / "Mode Costs.csv",
    ]
    
    missing_files = []
    for file in required_files:
        if not file.exists():
            missing_files.append(str(file.relative_to(datasets_path.parent)))
    
    if missing_files:
        print(f"⚠️  Missing dataset files: {missing_files}")
        print("Some features may not work correctly")
        return False
    
    print("✓ All required datasets found")
    return True

def setup_directories():
    """Create required directories"""
    ensure_directories(
        WEB_TEMPLATES_DIR,
        Q_TABLES_DIR,
        TRAINING_METRICS_DIR,
        SIMULATION_OUTPUTS_DIR,
        SHIPMENT_LOGS_DIR,
    )
    print("✓ Required directories created")

def start_application():
    """Start the LAHSO web application"""
    if not check_requirements():
        sys.exit(1)
    
    check_datasets()  # Warning only, don't exit
    setup_directories()
    
    print("🚀 Starting LAHSO Web Application...")
    print("📡 URL: http://localhost:5001")
    print("🔧 Production mode")
    print("📊 All LAHSO functionality integrated")
    print("🛑 Press Ctrl+C to stop")
    
    from lahso.web import create_app, socketio

    app = create_app()
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)

if __name__ == '__main__':
    start_application()
