"""
Sentinel Hub API processor for NDVI calculation
This module uses Sentinel Hub API to fetch and process Sentinel-2 data
"""

from sentinelhub import (
    SHConfig,
    CRS,
    BBox,
    DataCollection,
    MimeType,
    SentinelHubRequest,
    bbox_to_dimensions,
)
from datetime import datetime, timedelta
import numpy as np
from shapely.geometry import Polygon, Point
from PIL import Image

# Use non-GUI backend for matplotlib (fixes threading issues in Flask)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

import io
import base64


def setup_config(instance_id, client_id, client_secret):
    """
    Set up Sentinel Hub configuration

    Args:
        instance_id: Sentinel Hub instance ID
        client_id: OAuth client ID
        client_secret: OAuth client secret

    Returns:
        Configured SHConfig object
    """
    config = SHConfig()
    config.instance_id = instance_id
    config.sh_client_id = client_id
    config.sh_client_secret = client_secret

    return config


def polygon_to_bbox(polygon_coords):
    """
    Convert polygon coordinates to bounding box

    Args:
        polygon_coords: List of [lon, lat] coordinates

    Returns:
        BBox object
    """
    lons = [coord[0] for coord in polygon_coords]
    lats = [coord[1] for coord in polygon_coords]

    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    # Create bounding box
    bbox = BBox(bbox=[min_lon, min_lat, max_lon, max_lat], crs=CRS.WGS84)

    return bbox


def create_polygon_mask(polygon_coords, bbox, image_shape):
    """
    Create a mask array for pixels inside the polygon

    Args:
        polygon_coords: List of [lon, lat] coordinates defining the polygon
        bbox: BBox object representing the bounding box
        image_shape: Tuple (height, width) of the image array

    Returns:
        Boolean numpy array where True = inside polygon, False = outside
    """
    # Create shapely polygon from coordinates
    polygon = Polygon([(coord[0], coord[1]) for coord in polygon_coords])

    # Get bbox dimensions
    min_lon, min_lat = bbox.min_x, bbox.min_y
    max_lon, max_lat = bbox.max_x, bbox.max_y

    height, width = image_shape

    # Create mesh of pixel coordinates in geographic space
    lon_step = (max_lon - min_lon) / width
    lat_step = (max_lat - min_lat) / height

    # Create mask array
    mask = np.zeros(image_shape, dtype=bool)

    # Check each pixel center to see if it's inside the polygon
    for i in range(height):
        for j in range(width):
            # Calculate the geographic coordinates of pixel center
            # Note: image coordinates are top-down, but lat increases bottom-up
            pixel_lon = min_lon + (j + 0.5) * lon_step
            pixel_lat = max_lat - (i + 0.5) * lat_step

            # Check if point is inside polygon
            point = Point(pixel_lon, pixel_lat)
            mask[i, j] = polygon.contains(point)

    return mask


def create_ndvi_evalscript():
    """
    Create evalscript for NDVI calculation
    Sentinel Hub uses JavaScript-like evalscripts to process data

    Returns:
        Evalscript string
    """
    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: [{
                bands: ["B04", "B08", "dataMask"]
            }],
            output: [
                {
                    id: "ndvi",
                    bands: 1,
                    sampleType: "FLOAT32"
                },
                {
                    id: "dataMask",
                    bands: 1
                }
            ]
        };
    }

    function evaluatePixel(sample) {
        let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);

        // Handle invalid values
        if (sample.B08 + sample.B04 === 0) {
            ndvi = -999;
        }

        return {
            ndvi: [ndvi],
            dataMask: [sample.dataMask]
        };
    }
    """
    return evalscript


# calculate statistical metrics from NDVI values
def calculate_ndvi_statistics(ndvi_array, polygon_mask=None):
    """
    Calculate statistics from NDVI array

    Args:
        ndvi_array: 2D numpy array of NDVI values
        polygon_mask: Optional boolean mask for pixels inside polygon

    Returns:
        Dictionary with statistics
    """
    # Mask invalid values
    valid_mask = (ndvi_array > -1) & (ndvi_array < 1) & (ndvi_array != -999)

    # If polygon mask is provided, combine it with valid mask
    if polygon_mask is not None:
        valid_mask = valid_mask & polygon_mask

    valid_ndvi = ndvi_array[valid_mask]

    if len(valid_ndvi) == 0:
        return {
            'mean': 0.0,
            'min': 0.0,
            'max': 0.0,
            'std': 0.0
        }

    stats = {
        'mean': float(np.mean(valid_ndvi)),
        'min': float(np.min(valid_ndvi)),
        'max': float(np.max(valid_ndvi)),
        'std': float(np.std(valid_ndvi))
    }

    return stats

#creates an image with legend for the sidebar
#send to front in base64
def create_ndvi_visualization(ndvi_array, title='NDVI Visualization', polygon_mask=None):
    """
    Create a visualization of NDVI data for sidebar display

    Args:
        ndvi_array: NDVI data as numpy array
        title: Plot title
        polygon_mask: Optional boolean mask for pixels inside polygon

    Returns:
        Base64 encoded PNG image
    """
    # Mask invalid values
    ndvi_masked = np.copy(ndvi_array).astype(float)
    ndvi_masked[(ndvi_array < -1) | (ndvi_array > 1) | (ndvi_array == -999)] = np.nan

    # Apply polygon mask if provided (make pixels outside polygon transparent)
    if polygon_mask is not None:
        ndvi_masked[~polygon_mask] = np.nan

    fig, ax = plt.subplots(figsize=(10, 8))

    # Create the NDVI plot with RdYlGn colormap (red-yellow-green)
    im = ax.imshow(ndvi_masked, cmap='RdYlGn', vmin=-1, vmax=1, interpolation='bilinear')

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('NDVI', rotation=270, labelpad=20, fontsize=12)

    # Set title
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.axis('off')

    # Add NDVI interpretation legend
    interpretation = (
        'NDVI Interpretation:\n'
        '0.6 - 1.0: Dense vegetation\n'
        '0.2 - 0.6: Moderate vegetation\n'
        '0.0 - 0.2: Sparse vegetation\n'
        '< 0.0: Water/Snow'
    )
    ax.text(0.02, 0.98, interpretation, transform=ax.transAxes,
            fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    # Convert to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150, facecolor='white', transparent=False)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')

    # Clean up to prevent memory leaks
    buf.close()
    plt.close(fig)
    plt.close('all')  # Close all figures to be safe

    return image_base64

#creates a clean transparent png to overlay on the map
def create_ndvi_overlay_image(ndvi_array, polygon_mask=None):
    """
    Create a clean NDVI overlay image for map (no legend, title, or colorbar)

    Args:
        ndvi_array: NDVI data as numpy array
        polygon_mask: Optional boolean mask for pixels inside polygon

    Returns:
        Base64 encoded PNG image with transparency
    """
    # Mask invalid values
    ndvi_masked = np.copy(ndvi_array).astype(float)
    ndvi_masked[(ndvi_array < -1) | (ndvi_array > 1) | (ndvi_array == -999)] = np.nan

    # Apply polygon mask if provided (make pixels outside polygon NaN)
    if polygon_mask is not None:
        ndvi_masked[~polygon_mask] = np.nan

    # Get dimensions
    height, width = ndvi_array.shape

    # Create colormap and normalize
    cmap = plt.cm.RdYlGn
    norm = mcolors.Normalize(vmin=-1, vmax=1)

    # Apply colormap to get RGBA array (values 0-1)
    rgba_float = cmap(norm(ndvi_masked))

    # Convert to 0-255 range
    rgba_array = (rgba_float * 255).astype(np.uint8)

    # Set alpha channel to 0 (transparent) where data is NaN
    alpha_channel = np.where(np.isnan(ndvi_masked), 0, 255).astype(np.uint8)
    rgba_array[:, :, 3] = alpha_channel

    # Convert to PIL Image
    img = Image.fromarray(rgba_array, mode='RGBA')

    # Convert to base64
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=False)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')

    # Clean up
    buf.close()

    return image_base64

# main orchestrator : fetches sat data from api and process everything
# 
def get_ndvi_from_sentinelhub(polygon_coords, start_date, end_date, config):
    """
    Fetch NDVI data from Sentinel Hub for a given polygon

    Args:
        polygon_coords: List of [lon, lat] coordinates
        start_date: Start date as datetime or string (YYYY-MM-DD)
        end_date: End date as datetime or string (YYYY-MM-DD)
        config: SHConfig object with credentials

    Returns:
        Dictionary with NDVI data and statistics
    """
    try:
        # Convert polygon to bounding box
        bbox = polygon_to_bbox(polygon_coords)

        # Calculate appropriate resolution (max 512x512 for free tier)
        bbox_size = bbox_to_dimensions(bbox, resolution=10)

        # Limit size to avoid exceeding processing units
        max_size = 512
        if bbox_size[0] > max_size or bbox_size[1] > max_size:
            scale = min(max_size / bbox_size[0], max_size / bbox_size[1])
            bbox_size = (int(bbox_size[0] * scale), int(bbox_size[1] * scale))

        # Convert dates to datetime if they're strings
        if isinstance(start_date, str):
            if len(start_date) == 8:  # YYYYMMDD format
                start_date = datetime.strptime(start_date, '%Y%m%d')
            else:  # YYYY-MM-DD format
                start_date = datetime.strptime(start_date, '%Y-%m-%d')

        if isinstance(end_date, str):
            if len(end_date) == 8:  # YYYYMMDD format
                end_date = datetime.strptime(end_date, '%Y%m%d')
            else:  # YYYY-MM-DD format
                end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Create the request
        evalscript = create_ndvi_evalscript()

        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL2_L2A,
                    time_interval=(start_date, end_date),
                    maxcc=0.3,  # Maximum cloud coverage 30%
                )
            ],
            responses=[
                SentinelHubRequest.output_response('ndvi', MimeType.TIFF),
            ],
            bbox=bbox,
            size=bbox_size,
            config=config,
        )

        # Get the data
        ndvi_data = request.get_data()

        if not ndvi_data or len(ndvi_data) == 0:
            raise ValueError("No data returned from Sentinel Hub")

        # Extract NDVI array (first image if multiple dates)
        ndvi_array = ndvi_data[0]

        # If it's 3D, take the first band
        if len(ndvi_array.shape) == 3:
            ndvi_array = ndvi_array[:, :, 0]

        # Create polygon mask to only show NDVI within the drawn polygon
        polygon_mask = create_polygon_mask(polygon_coords, bbox, ndvi_array.shape)

        # Calculate statistics (only for pixels inside polygon)
        stats = calculate_ndvi_statistics(ndvi_array, polygon_mask)

        # Create visualization for sidebar (with legend and colorbar)
        image_base64 = create_ndvi_visualization(ndvi_array, f'NDVI - {end_date.strftime("%Y-%m-%d")}', polygon_mask)

        # Create clean overlay image for map (no legend, transparent background)
        overlay_image_base64 = create_ndvi_overlay_image(ndvi_array, polygon_mask)

        # Extract bbox coordinates for map overlay [min_lon, min_lat, max_lon, max_lat]
        bbox_coords = [
            [bbox.min_y, bbox.min_x],  # Southwest corner [lat, lon]
            [bbox.max_y, bbox.max_x]   # Northeast corner [lat, lon]
        ]

        # Convert NDVI array to list for JSON serialization (for hover functionality)
        ndvi_list = ndvi_array.tolist()

        return {
            'success': True,
            'ndvi_stats': stats,
            'ndvi_image': image_base64,  # For sidebar display
            'ndvi_overlay': overlay_image_base64,  # For map overlay
            'ndvi_array': ndvi_list,  # For hover functionality
            'bbox_size': bbox_size,
            'bbox': bbox_coords  # For Leaflet imageOverlay
        }

    except Exception as e:
        raise Exception(f"Error fetching NDVI from Sentinel Hub: {str(e)}")

#calculate_ndvi_statistics
#create_ndvi_visualization
#create_ndvi_overlay_image
#get_ndvi_from_sentinelhub

# Example usage
if __name__ == "__main__":
    # Example configuration
    config = setup_config(
        instance_id="your_instance_id",
        client_id="your_client_id",
        client_secret="your_client_secret"
    )

    # Example polygon (small area in Europe)
    polygon = [
        [13.822, 45.850],
        [13.830, 45.850],
        [13.830, 45.855],
        [13.822, 45.855],
        [13.822, 45.850]
    ]

    # Get NDVI
    result = get_ndvi_from_sentinelhub(
        polygon,
        datetime(2024, 6, 1),
        datetime(2024, 6, 30),
        config
    )

    print(f"NDVI Stats: {result['ndvi_stats']}")
