# Flask NDVI Calculator with Sentinel-2

A Flask web application for calculating multiple crop indexes like the NDVI (Normalized Difference Vegetation Index) from Sentinel-2 satellite imagery. Users can draw polygons on an interactive map to define zones of interest, and the application will download Sentinel-2 data and calculate vegetation indices.

## Features

- Interactive Leaflet map with satellite images and drawing tools
- Draw custom polygons to define areas of interest
- Integration with Sentinel-2 satellite data via SentinelSat API
- Automatic NDVI calculation from NIR and Red bands
- Visual representation of NDVI with color-coded heatmaps
- Cloud cover filtering (< 30%)
- Date range selection for satellite imagery
- Real-time statistics (mean, min, max NDVI)

## Prerequisites

- Python 3.8 or higher
- Copernicus Open Access Hub account (free registration required)

## Installation

1. Clone or download this repository

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Register for a free Copernicus account:
   - Visit: https://scihub.copernicus.eu/dhus/#/self-registration
   - Complete the registration and verify your email
   - You'll receive credentials to access Sentinel data

4. Create a `.env` file in the project root with your credentials:
```bash
SENTINEL_INSTANCE_ID=your_instance_id_here
SENTINEL_CLIENT_ID=your_client_id_here
SENTINEL_CLIENT_SECRET=your_client_secret_here

```

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

3. Use the application:
   - Use the polygon drawing tool on the map to select an area
   - Choose a date range (default: last 30 days)
   - Click "Calculate NDVI" to process
   - View the NDVI statistics and visualization in the sidebar

## How It Works

1. **Polygon Selection**: Users draw a polygon on the interactive map to define the area of interest
2. **Sentinel Query**: The application queries the Sentinel-2 satellite data archive for images matching:
   - The selected geographic area
   - The specified date range
   - Cloud cover < 30%
3. **Data Download**: The most recent, clearest image is downloaded
4. **NDVI Calculation**: The application extracts NIR (Band 8) and Red (Band 4) bands and calculates:
   ```
   NDVI = (NIR - Red) / (NIR + Red)
   ```
5. **Visualization**: Results are displayed as statistics and a color-coded heatmap

## NDVI Interpretation

- **0.6 to 1.0**: Dense vegetation (forests, crops in peak growth)
- **0.2 to 0.6**: Moderate vegetation (grasslands, shrubs)
- **0.0 to 0.2**: Sparse vegetation or bare soil
- **Negative values**: Water, snow, clouds

## Project Structure

```
flask_sentinel_claude/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Frontend interface
├── downloads/            # Satellite data storage (auto-created)
└── static/              # Static assets (auto-created)
```

## API Endpoints

### `GET /`
Renders the main application interface

### `POST /api/calculate-ndvi`
Calculate NDVI for a given polygon

**Request Body:**
```json
{
  "polygon": [[lon, lat], ...],
  "start_date": "20240101",
  "end_date": "20240201"
}
```

**Response:**
```json
{
  "success": true,
  "ndvi_stats": {
    "mean": 0.65,
    "min": 0.2,
    "max": 0.9
  },
  "ndvi_image": "base64_encoded_image",
  "product_info": {
    "date": "2024-01-15",
    "cloud_cover": 5.3
  }
}
```

### `GET /api/health`
Health check endpoint

## Important Notes

1. **First Download**: The first time you download a Sentinel-2 product, it may take several minutes as the data files are large (hundreds of MB to several GB)

2. **Storage**: Downloaded satellite images are stored in the `downloads/` folder. Consider implementing cleanup for old files in production.

3. **Processing Level**: This implementation works with both L1C (Top of Atmosphere) and L2A (Bottom of Atmosphere) Sentinel-2 products.

4. **Production Considerations**:
   - Implement background job processing (Celery, RQ) for long-running downloads
   - Add caching for frequently requested areas
   - Implement proper error handling and logging
   - Add authentication if deploying publicly
   - Consider using cloud-optimized GeoTIFFs for faster processing

## Troubleshooting

### "Sentinel credentials not configured"
- Make sure you've created a `.env` file with your credentials
- Verify your credentials are correct by logging into https://scihub.copernicus.eu/dhus/

### "No Sentinel-2 images found"
- Try expanding your date range
- Select a different geographic area
- Check if there's satellite coverage for your selected region

### Slow performance
- First-time downloads can take 5-10 minutes for large areas
- Consider reducing the polygon size
- Ensure stable internet connection

## Future Enhancements

- [ ] Support for other vegetation indices (EVI, SAVI, MSAVI)
- [ ] Time-series analysis
- [ ] Export results as GeoTIFF or shapefile
- [ ] Compare multiple dates
- [ ] Integration with Google Earth Engine as alternative data source
- [ ] Implement proper band extraction from .SAFE files
- [ ] Add user authentication
- [ ] Background job processing
- [ ] Data caching system

## License

MIT License

## Credits

- Sentinel-2 data: ESA Copernicus Programme
- Map interface: Leaflet.js
- Satellite data access: SentinelSat library
