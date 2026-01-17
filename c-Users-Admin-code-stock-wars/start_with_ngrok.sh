#!/bin/bash
echo "Starting Flask app with ngrok..."
echo ""

# Start Flask in background
python app.py &
FLASK_PID=$!

# Wait for Flask to start
sleep 3

# Start ngrok
echo "Starting ngrok tunnel..."
ngrok http 5000

# Cleanup on exit
trap "kill $FLASK_PID" EXIT









