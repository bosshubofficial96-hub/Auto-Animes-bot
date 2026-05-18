#!/bin/bash

# Stop script for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦

echo "🛑 Stopping ✦ ＡＵＴＯ ＡＮＩＭＥ ✦ Bot..."

# Find the process
PID=$(ps aux | grep "python3 -m bot.main" | grep -v grep | awk '{print $2}')

if [ -z "$PID" ]; then
    echo "❌ Bot is not running"
    exit 0
fi

# Kill the process
echo "Killing process $PID..."
kill $PID

# Wait for process to terminate
sleep 2

# Force kill if still running
if ps -p $PID > /dev/null 2>&1; then
    echo "Force killing process..."
    kill -9 $PID
fi

echo "✅ Bot stopped successfully"
