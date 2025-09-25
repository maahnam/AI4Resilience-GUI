"""
LAHSO Web Application Setup Script
"""
import os
import shutil
from pathlib import Path

def main():
    print("🔧 Setting up LAHSO Web Application...")
    
    # Create required directories
    directories = [
        'templates',
        'q_table',
        'training', 
        'csv_output',
        'shipment_logs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")
    
    # Check if templates/index.html exists
    if not Path('templates/index.html').exists():
        print("❌ templates/index.html not found!")
        print("Please copy the HTML content to templates/index.html")
    else:
        print("✓ templates/index.html found")
    
    # Check if Datasets exist
    if not Path('Datasets').exists():
        print("⚠️  Datasets directory not found")
        print("Please copy your LAHSO datasets to a Datasets/ folder")
    else:
        print("✓ Datasets directory found")
    
    print("\n📋 Setup complete! Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Install and configure Gurobi")
    print("3. Copy HTML content to templates/index.html")
    print("4. Ensure Datasets/ folder contains your LAHSO data")
    print("5. Run: python run_web.py")

if __name__ == '__main__':
    main()