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

# Use non-GUI backend for matplotlib (fixes threading issues in Flask)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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


def calculate_ndvi_statistics(ndvi_array):
    """
    Calculate statistics from NDVI array

    Args:
        ndvi_array: 2D numpy array of NDVI values

    Returns:
        Dictionary with statistics
    """
    # Mask invalid values
    valid_mask = (ndvi_array > -1) & (ndvi_array < 1) & (ndvi_array != -999)
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


def create_ndvi_visualization(ndvi_array, title='NDVI Visualization'):
    """
    Create a visualization of NDVI data

    Args:
        ndvi_array: NDVI data as numpy array
        title: Plot title

    Returns:
        Base64 encoded PNG image
    """
    # Mask invalid values
    ndvi_masked = np.copy(ndvi_array)
    ndvi_masked[(ndvi_array < -1) | (ndvi_array > 1) | (ndvi_array == -999)] = np.nan

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
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=150, facecolor='white')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')

    # Clean up to prevent memory leaks
    buf.close()
    plt.close(fig)
    plt.close('all')  # Close all figures to be safe

    return image_base64


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

        # Calculate statistics
        stats = calculate_ndvi_statistics(ndvi_array)

        # Create visualization
        image_base64 = create_ndvi_visualization(ndvi_array, f'NDVI - {end_date.strftime("%Y-%m-%d")}')

        # Extract bbox coordinates for map overlay [min_lon, min_lat, max_lon, max_lat]
        bbox_coords = [
            [bbox.min_y, bbox.min_x],  # Southwest corner [lat, lon]
            [bbox.max_y, bbox.max_x]   # Northeast corner [lat, lon]
        ]

        return {
            'success': True,
            'ndvi_stats': stats,
            'ndvi_image': image_base64,
            'ndvi_array': ndvi_array,
            'bbox_size': bbox_size,
            'bbox': bbox_coords  # For Leaflet imageOverlay
        }

    except Exception as e:
        raise Exception(f"Error fetching NDVI from Sentinel Hub: {str(e)}")


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
