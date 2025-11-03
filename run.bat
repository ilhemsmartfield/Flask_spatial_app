@echo off
echo ====================================
echo Flask NDVI Calculator with Sentinel-2
echo ====================================
echo.

REM Check if .env file exists
if not exist .env (
    echo WARNING: .env file not found!
    echo Please create a .env file with your Sentinel credentials.
    echo You can copy .env.example to .env and fill in your credentials.
    echo.
    echo To register for Sentinel Hub credentials, visit:
    echo https://scihub.copernicus.eu/dhus/#/self-registration
    echo.
    pause
)

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt
echo.

REM Run the Flask application
echo Starting Flask application...
echo.
echo The application will be available at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.
python app.py
