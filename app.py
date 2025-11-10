from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import numpy as np
import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import io
import base64
from dotenv import load_dotenv
from sentinelhub_processor import setup_config, get_ndvi_from_sentinelhub

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static', exist_ok=True)

# Sentinel Hub credentials
SENTINEL_INSTANCE_ID = os.environ.get('SENTINEL_INSTANCE_ID', '')
SENTINEL_CLIENT_ID = os.environ.get('SENTINEL_CLIENT_ID', '')
SENTINEL_CLIENT_SECRET = os.environ.get('SENTINEL_CLIENT_SECRET', '')


@app.route('/')
def index():
    """Render the main page with the map interface"""
    return render_template('index.html')


@app.route('/api/calculate-ndvi', methods=['POST'])
def calculate_ndvi():
    """
    Calculate NDVI for a given polygon area using Sentinel Hub API
    Expects JSON with polygon coordinates and date range
    """
    try:
        data = request.json
        polygon_coords = data.get('polygon')
        start_date = data.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y%m%d'))
        end_date = data.get('end_date', datetime.now().strftime('%Y%m%d'))

        if not polygon_coords:
            return jsonify({'error': 'No polygon coordinates provided'}), 400

        # Check if Sentinel Hub credentials are available
        if not all([SENTINEL_INSTANCE_ID, SENTINEL_CLIENT_ID, SENTINEL_CLIENT_SECRET]):
            return jsonify({
                'error': 'Sentinel Hub credentials not configured. Please set credentials in .env file.',
                'info': 'Get credentials at https://www.sentinel-hub.com/'
            }), 500

        # Set up Sentinel Hub configuration
        config = setup_config(
            SENTINEL_INSTANCE_ID,
            SENTINEL_CLIENT_ID,
            SENTINEL_CLIENT_SECRET
        )

        # Get NDVI data from Sentinel Hub
        result = get_ndvi_from_sentinelhub(
            polygon_coords,
            start_date,
            end_date,
            config
        )

        return jsonify({
            'success': True,
            'ndvi_stats': result['ndvi_stats'],
            'ndvi_image': result['ndvi_image'],
            'bbox': result.get('bbox', None),  # Bounding box for map overlay
            'product_info': {
                'date': end_date,
                'cloud_cover': 'N/A',  # Sentinel Hub filters automatically
                'resolution': f"{result['bbox_size'][0]}x{result['bbox_size'][1]} pixels"
            }
        })

    except Exception as e:
        # If real processing fails, provide helpful error message
        error_msg = str(e)

        print(f"Error calculating NDVI: {error_msg}")

        # Check for common errors
        if "credentials" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
            return jsonify({
                'error': 'Authentication failed. Please check your Sentinel Hub credentials.',
                'details': error_msg
            }), 401
        elif "quota" in error_msg.lower() or "429" in error_msg:
            return jsonify({
                'error': 'Processing quota exceeded. Please try again later or upgrade your Sentinel Hub plan.',
                'details': error_msg
            }), 429
        elif "No data" in error_msg:
            return jsonify({
                'error': 'No satellite data found for this area and date range.',
                'info': 'Try expanding the date range or selecting a different area.',
                'details': error_msg
            }), 404
        else:
            return jsonify({
                'error': f'Error processing NDVI: {error_msg}',
                'info': 'Please check your inputs and try again.'
            }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    credentials_configured = all([
        SENTINEL_INSTANCE_ID,
        SENTINEL_CLIENT_ID,
        SENTINEL_CLIENT_SECRET
    ])

    return jsonify({
        'status': 'ok',
        'sentinel_configured': credentials_configured,
        'api_type': 'Sentinel Hub',
        'credentials': {
            'instance_id': 'configured' if SENTINEL_INSTANCE_ID else 'missing',
            'client_id': 'configured' if SENTINEL_CLIENT_ID else 'missing',
            'client_secret': 'configured' if SENTINEL_CLIENT_SECRET else 'missing'
        }
    })


if __name__ == '__main__':
    print("=" * 60)
    print("Flask NDVI Calculator with Sentinel Hub")
    print("=" * 60)
    print(f"Instance ID: {'✓ Configured' if SENTINEL_INSTANCE_ID else '✗ Missing'}")
    print(f"Client ID: {'✓ Configured' if SENTINEL_CLIENT_ID else '✗ Missing'}")
    print(f"Client Secret: {'✓ Configured' if SENTINEL_CLIENT_SECRET else '✗ Missing'}")
    print("=" * 60)
    print("Starting server at http://localhost:5000")
    print("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=5000)
