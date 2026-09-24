#!/usr/bin/env python3
"""
Unified Launcher for Cost Driver Dashboard & Savings Tracker
Runs both Streamlit apps simultaneously with separate ports
"""
import subprocess
import time
import sys
import os
from pathlib import Path

# Define paths
ROOT = Path(__file__).parent
COST_DRIVER = ROOT / "app.py"
SAVINGS_TRACKER = ROOT / "modules" / "savings-tracker" / "app.py"

# Streamlit ports
COST_DRIVER_PORT = 8501
SAVINGS_TRACKER_PORT = 8502

def run_streamlit(app_path, port, name):
    """Launch a Streamlit app on a specific port."""
    env = os.environ.copy()
    env["STREAMLIT_SERVER_PORT"] = str(port)
    env["STREAMLIT_SERVER_ADDRESS"] = "localhost"
    
    print(f"\n🚀 Launching {name} on http://localhost:{port}")
    
    return subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(app_path),
         "--logger.level=info"],
        env=env,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

def main():
    print("=" * 70)
    print("📊 UNIFIED SOURCING ANALYTICS DASHBOARD")
    print("=" * 70)
    
    # Check if apps exist
    if not COST_DRIVER.exists():
        print(f"❌ Cost Driver app not found: {COST_DRIVER}")
        sys.exit(1)
    if not SAVINGS_TRACKER.exists():
        print(f"❌ Savings Tracker app not found: {SAVINGS_TRACKER}")
        sys.exit(1)
    
    try:
        # Launch both apps
        print("\n📋 Starting both applications...\n")
        
        p1 = run_streamlit(COST_DRIVER, COST_DRIVER_PORT, "Cost Driver Dashboard")
        time.sleep(2)  # Stagger startup
        p2 = run_streamlit(SAVINGS_TRACKER, SAVINGS_TRACKER_PORT, "Savings & Negotiation Tracker")
        
        print("\n" + "=" * 70)
        print("✅ BOTH APPS ARE RUNNING!")
        print("=" * 70)
        print(f"\n📊 Cost Driver Dashboard:     http://localhost:{COST_DRIVER_PORT}")
        print(f"💰 Savings Tracker:           http://localhost:{SAVINGS_TRACKER_PORT}")
        print("\n💡 Workflow:")
        print("   1. Use Cost Driver Dashboard to identify cost drivers & opportunities")
        print("   2. Use Savings Tracker to record & track savings initiatives")
        print("   3. Monitor realization rate to see if promised savings land")
        print("\n⚠️  Press Ctrl+C to stop both apps\n")
        
        # Wait for both processes
        p1.wait()
        p2.wait()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping both applications...")
        p1.terminate()
        p2.terminate()
        time.sleep(1)
        p1.kill()
        p2.kill()
        print("✅ Both apps stopped gracefully.")
        sys.exit(0)

if __name__ == "__main__":
    main()
