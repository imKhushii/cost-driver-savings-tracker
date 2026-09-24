#!/bin/bash

# Unified launcher for Cost Driver Dashboard & Savings Tracker
# Runs both Streamlit apps simultaneously

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COST_DRIVER_PORT=8501
SAVINGS_TRACKER_PORT=8502

echo "========================================================================"
echo "📊 UNIFIED SOURCING ANALYTICS DASHBOARD"
echo "========================================================================"
echo ""
echo "🚀 Starting both applications..."
echo ""

# Activate Cost Driver environment & run
cd "$ROOT"
source .venv/bin/activate
echo "📊 Launching Cost Driver Dashboard on http://localhost:$COST_DRIVER_PORT"
STREAMLIT_SERVER_PORT=$COST_DRIVER_PORT streamlit run app.py &
COST_DRIVER_PID=$!

sleep 2

# Activate Savings Tracker environment & run
cd "$ROOT/modules/savings-tracker"
source .venv/bin/activate
echo "💰 Launching Savings Tracker on http://localhost:$SAVINGS_TRACKER_PORT"
STREAMLIT_SERVER_PORT=$SAVINGS_TRACKER_PORT streamlit run app.py &
SAVINGS_TRACKER_PID=$!

echo ""
echo "========================================================================"
echo "✅ BOTH APPS ARE RUNNING!"
echo "========================================================================"
echo ""
echo "📊 Cost Driver Dashboard:     http://localhost:$COST_DRIVER_PORT"
echo "💰 Savings Tracker:           http://localhost:$SAVINGS_TRACKER_PORT"
echo ""
echo "💡 Workflow:"
echo "   1. Use Cost Driver Dashboard to identify cost drivers & opportunities"
echo "   2. Use Savings Tracker to record & track savings initiatives"
echo "   3. Monitor realization rate to see if promised savings land"
echo ""
echo "⚠️  Press Ctrl+C to stop both apps"
echo ""

# Wait for both processes
wait $COST_DRIVER_PID $SAVINGS_TRACKER_PID
