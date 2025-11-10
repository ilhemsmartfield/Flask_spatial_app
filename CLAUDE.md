# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Flask web application for calculating NDVI (Normalized Difference Vegetation Index) from Sentinel-2 satellite imagery via Sentinel Hub API. Users draw polygons on an interactive Leaflet map with satellite/street view layers, and the application calculates and overlays vegetation health data directly on the map.

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure Sentinel Hub credentials in .env
SENTINEL_INSTANCE_ID=your_instance_id
SENTINEL_CLIENT_ID=your_client_id
SENTINEL_CLIENT_SECRET=your_client_secret

# Run the application
python app.py
# Server runs at http://localhost:5000
```

## Architecture

### Backend (Flask)
- **app.py**: Main Flask application with API endpoints
  - `GET /`: Serves the main UI
  - `POST /api/calculate-ndvi`: Processes polygon and returns NDVI data
  - `GET /api/health`: Health check with credential status

- **sentinelhub_processor.py**: Core NDVI processing logic
  - `get_ndvi_from_sentinelhub()`: Main function that orchestrates NDVI calculation
  - `create_polygon_mask()`: Creates boolean mask for pixels inside user-drawn polygon
  - `create_ndvi_visualization()`: Generates sidebar image with legend/colorbar
  - `create_ndvi_overlay_image()`: Generates clean transparent PNG for map overlay (vectorized NumPy operations for performance)
  - Returns both `ndvi_image` (sidebar) and `ndvi_overlay` (map) plus `ndvi_array` for hover functionality

### Frontend (templates/index.html)
Single-page application with:
- **Leaflet map** with two base layers (Street/Satellite via Esri)
- **Drawing tools** for polygon creation
- **Layer switcher**: Base Map / NDVI Layer (like Excel sheet tabs)
- **NDVI overlay**: Transparent PNG showing colors only within polygon boundaries
- **Hover functionality**: Displays real-time NDVI values and coordinates when mouse moves over NDVI layer
- **Sidebar**: Statistics, visualization with legend, color scale reference, and hover info card

### Key Data Flow

1. User draws polygon → Frontend collects GeoJSON coordinates
2. POST to `/api/calculate-ndvi` with polygon coordinates and date range
3. Backend:
   - Converts polygon to bounding box for Sentinel Hub query
   - Fetches satellite imagery via Sentinel Hub API
   - Creates polygon mask (boolean array matching image dimensions)
   - Calculates NDVI only for pixels inside polygon
   - Generates two images:
     - Sidebar visualization (with legend/colorbar)
     - Clean overlay (transparent PNG, fully opaque NDVI colors inside polygon)
   - Returns NDVI stats, both images, and raw array data
4. Frontend:
   - Displays stats and visualization in sidebar
   - Overlays clean NDVI image on map at correct geographic bounds
   - Shows NDVI legend in separate card
   - Enables hover to show per-pixel NDVI values

## Critical Implementation Details

### Polygon Masking
The application masks NDVI to show **only pixels inside the user-drawn polygon**:
- `create_polygon_mask()` uses Shapely to check each pixel's geographic center against polygon
- Mask is applied to both statistics calculation and visualization
- Outside pixels set to NaN → transparent in overlay image

### NDVI Overlay Generation
**Must be fast and produce vivid colors:**
- Use vectorized NumPy operations (NOT pixel loops)
- `create_ndvi_overlay_image()` uses `cmap(norm(ndvi_masked))` to apply colormap to entire array
- Alpha channel set via `np.where(np.isnan(ndvi_masked), 0, 255)`
- Results in RGBA image: opaque (255) inside polygon, transparent (0) outside
- PIL/Pillow converts to PNG

### Layer Management
- Track `currentLayer` state ('base' or 'ndvi')
- Hover info only shows when `currentLayer === 'ndvi'`
- When switching to NDVI layer: polygon becomes transparent with red dashed border
- When switching to base layer: polygon shows blue fill

### Hover Functionality
Map mousemove event calculates pixel position from lat/lng:
```javascript
// Convert geographic coordinates to pixel indices
const relX = (lng - west) / (east - west);
const relY = (north - lat) / (north - south);
const pixelX = Math.floor(relX * width);
const pixelY = Math.floor(relY * height);
const ndviValue = ndviData[pixelY][pixelX];
```

## Common Issues

### NDVI overlay not visible or too faint
- Check `create_ndvi_overlay_image()` is using vectorized NumPy operations
- Verify alpha channel is set to 255 for valid pixels
- Default opacity should be 0.85 (adjustable via slider)

### Polygon mask not working correctly
- Ensure `create_polygon_mask()` calculates pixel centers correctly accounting for image coordinates (top-down) vs lat coordinates (bottom-up)
- Mask must be boolean array matching `ndvi_array.shape`

### Slow NDVI processing
- Check for pixel-by-pixel loops (replace with vectorized NumPy)
- Sentinel Hub API limits image size to 512x512 for free tier
- `bbox_to_dimensions()` automatically scales if needed

## Sentinel Hub API Notes

- Uses **evalscript** (JavaScript-like) to calculate NDVI server-side
- Fetches B04 (Red) and B08 (NIR) bands from Sentinel-2 L2A
- Maximum cloud coverage filter: 30%
- Returns TIFF data converted to NumPy array

## Environment Variables

Required in `.env`:
```bash
SENTINEL_INSTANCE_ID=      # Sentinel Hub instance ID
SENTINEL_CLIENT_ID=        # OAuth client ID
SENTINEL_CLIENT_SECRET=    # OAuth client secret
```

Optional:
```bash
MAX_CLOUD_COVER=30         # Max cloud coverage percentage
OUTPUT_DPI=150             # Visualization DPI
NDVI_COLORMAP=RdYlGn      # Matplotlib colormap
```
