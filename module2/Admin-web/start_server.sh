#!/bin/bash

# Audio Dataset Management Server Startup Script

echo "🎵 Audio Dataset Management Server"
echo "================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade requirements
echo "📋 Installing requirements..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please create a .env file with your database configuration:"
    echo ""
    echo "DB_HOST=localhost"
    echo "DB_PORT=5432"
    echo "DB_NAME=your_database_name"
    echo "DB_USER=your_username"
    echo "DB_PASSWORD=your_password"
    echo ""
    echo "Press Enter to continue anyway, or Ctrl+C to exit and create .env file..."
    read
fi

echo "🚀 Starting server..."
echo "📱 Web Interface: http://localhost:8000"
echo "📖 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python run_server.py