#!/bin/bash

# Setup script for ✦ ＡＵＴＯ ＡＮＩＭＥ ✦

echo "🔧 Setting up ✦ ＡＵＴＯ ＡＮＩＭＥ ✦ Bot..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
if [ -z "$PYTHON_VERSION" ]; then
    echo "❌ Python 3 is not installed!"
    exit 1
fi

MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]); then
    echo "❌ Python 3.8+ is required! Found $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg is not installed!"
    echo "Installing FFmpeg..."
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y ffmpeg
    elif command -v yum &> /dev/null; then
        sudo yum install -y ffmpeg
    elif command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        echo "❌ Please install FFmpeg manually"
        exit 1
    fi
fi

echo "✅ FFmpeg detected"

# Create virtual environment (optional)
read -p "Create virtual environment? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "✅ Virtual environment created and activated"
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p data/downloads
mkdir -p data/processed
mkdir -p data/temp
mkdir -p data/logs
mkdir -p data/backups

# Setup environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your bot token!"
else
    echo "✅ .env file already exists"
fi

# Make scripts executable
chmod +x scripts/*.sh

# Check bot token
if [ -f .env ]; then
    source .env
    if [ -z "$BOT_TOKEN" ] || [ "$BOT_TOKEN" = "YOUR_BOT_TOKEN_HERE" ]; then
        echo "⚠️  BOT_TOKEN not set in .env file!"
    else
        echo "✅ Bot token configured"
    fi
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your bot token"
echo "2. Run ./scripts/start.sh to start the bot"
echo "3. Add your bot to Telegram channels"
echo ""
echo "📖 For help: https://github.com/BOSSHUB/auto-anime-bot"
