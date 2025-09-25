#!/usr/bin/env python3
"""
LAHSO Web Application - Production Runner
"""
import os
import sys
from pathlib import Path

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
    datasets_path = Path('Datasets')
    if not datasets_path.exists():
        print("❌ Datasets directory not found")
        print("Please copy your LAHSO datasets to the Datasets/ folder")
        return False
    
    required_files = [
        'Network.csv',
        'Network_Barge.csv', 
        'Network_Train.csv',
        'Network_Truck.csv',
        'Fixed Vehicle Schedule.csv',
        'Truck Schedule.csv',
        'Mode Costs.csv'
    ]
    
    missing_files = []
    for file in required_files:
        if not (datasets_path / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"⚠️  Missing dataset files: {missing_files}")
        print("Some features may not work correctly")
        return False
    
    print("✓ All required datasets found")
    return True

def setup_directories():
    """Create required directories"""
    directories = ['templates', 'q_table', 'training', 'csv_output', 'shipment_logs']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
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
    
    from app import app, socketio
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)

if __name__ == '__main__':
    start_application()