#!/bin/bash

echo "===================================="
echo "Flask NDVI Calculator with Sentinel-2"
echo "===================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "WARNING: .env file not found!"
    echo "Please create a .env file with your Sentinel credentials."
    echo "You can copy .env.example to .env and fill in your credentials."
    echo ""
    echo "To register for Sentinel Hub credentials, visit:"
    echo "https://scihub.copernicus.eu/dhus/#/self-registration"
    echo ""
    read -p "Press Enter to continue..."
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt
echo ""

# Run the Flask application
echo "Starting Flask application..."
echo ""
echo "The application will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""
python app.py
