#!/bin/bash

# Start script for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦

echo "🚀 Starting ✦ ＡＵＴＯ ＡＮＩＭＥ ✦ Bot..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Create required directories
mkdir -p data/downloads data/processed data/temp data/logs data/backups

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
pip3 install -r requirements.txt --quiet

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found! Creating from .env.example..."
    cp .env.example .env
    echo "❌ Please edit .env file with your bot token and other settings!"
    exit 1
fi

# Start the bot
echo "🤖 Bot is starting..."
python3 -m bot.main

# Handle exit
if [ $? -eq 0 ]; then
    echo "✅ Bot stopped normally"
else
    echo "❌ Bot crashed with error code $?"
    exit 1
fi
