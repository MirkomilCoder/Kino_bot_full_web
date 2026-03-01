#!/bin/bash

# Kino Bot Deployment Script for Railway
# This script prepares and starts the bot

echo "🚀 Starting Kino Bot..."

# Install Python dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if required environment variables are set
if [ -z "$MAIN_BOT_TOKEN" ]; then
    echo "❌ Error: MAIN_BOT_TOKEN is not set"
    exit 1
fi

if [ -z "$MAIN_BOT_USERNAME" ]; then
    echo "❌ Error: MAIN_BOT_USERNAME is not set"
    exit 1
fi

if [ -z "$OWNER_ID" ]; then
    echo "❌ Error: OWNER_ID is not set"
    exit 1
fi

echo "✅ Environment variables verified"

# Create data directory if it doesn't exist
mkdir -p data

# Start the bot
echo "🎬 Bot is starting..."
python -m app.bot_main

