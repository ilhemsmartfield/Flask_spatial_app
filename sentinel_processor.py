"""
Sentinel-2 data processor for NDVI calculation
This module handles the extraction and processing of Sentinel-2 bands
"""

import os
import zipfile
import numpy as np
from shapely.geometry import shape
import matplotlib.pyplot as plt
import io
import base64

# Make rasterio optional for Windows compatibility
try:
    import rasterio
    from rasterio.mask import mask
    from rasterio.warp import calculate_default_transform, reproject, Resampling
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False
    print("Warning: rasterio not available. Real NDVI processing will not work.")


def extract_safe_file(zip_path, extract_dir):
    """
    Extract .SAFE file from downloaded zip

    Args:
        zip_path: Path to the downloaded .zip file
        extract_dir: Directory to extract to

    Returns:
        Path to extracted .SAFE directory
    """
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    # Find the .SAFE directory
    for item in os.listdir(extract_dir):
        if item.endswith('.SAFE'):
            return os.path.join(extract_dir, item)

    raise ValueError("No .SAFE directory found in extracted files")


def find_band_file(safe_dir, band_name, resolution='10m'):
    """
    Find the path to a specific band file in the .SAFE directory

    Args:
        safe_dir: Path to .SAFE directory
        band_name: Band identifier (e.g., 'B04', 'B08')
        resolution: Spatial resolution ('10m', '20m', '60m')

    Returns:
        Path to the band file
    """
    # Sentinel-2 structure: .SAFE/GRANULE/*/IMG_DATA/R{resolution}/{band}.jp2
    granule_dir = os.path.join(safe_dir, 'GRANULE')

    if not os.path.exists(granule_dir):
        raise ValueError(f"GRANULE directory not found in {safe_dir}")

    # Get the first granule (usually only one)
    granules = [d for d in os.listdir(granule_dir) if os.path.isdir(os.path.join(granule_dir, d))]
    if not granules:
        raise ValueError("No granule directories found")

    granule_path = os.path.join(granule_dir, granules[0])

    # Check for L2A structure (has R10m, R20m, R60m folders)
    img_data_dir = os.path.join(granule_path, 'IMG_DATA')
    resolution_dir = os.path.join(img_data_dir, f'R{resolution}')

    if os.path.exists(resolution_dir):
        # L2A structure
        band_files = [f for f in os.listdir(resolution_dir) if band_name in f and f.endswith('.jp2')]
    else:
        # L1C structure (bands directly in IMG_DATA)
        band_files = [f for f in os.listdir(img_data_dir) if band_name in f and f.endswith('.jp2')]
        resolution_dir = img_data_dir

    if not band_files:
        raise ValueError(f"Band {band_name} not found in {resolution_dir}")

    return os.path.join(resolution_dir, band_files[0])


def read_and_clip_band(band_path, geojson_polygon):
    """
    Read a band file and clip it to the polygon area

    Args:
        band_path: Path to the band .jp2 file
        geojson_polygon: GeoJSON polygon to clip to

    Returns:
        Clipped band data as numpy array
    """
    with rasterio.open(band_path) as src:
        # Convert GeoJSON to shapely geometry
        geom = shape(geojson_polygon['features'][0]['geometry'])

        # Ensure geometry is in the same CRS as the raster
        # You may need to reproject the geometry if CRS doesn't match

        # Clip the raster to the polygon
        out_image, out_transform = mask(src, [geom], crop=True, nodata=0)

        return out_image[0]  # Return first band (single-band image)


def calculate_ndvi(nir_band, red_band):
    """
    Calculate NDVI from NIR and Red bands

    NDVI = (NIR - Red) / (NIR + Red)

    Args:
        nir_band: Near-infrared band data (numpy array)
        red_band: Red band data (numpy array)

    Returns:
        NDVI array and statistics
    """
    # Convert to float to avoid integer division
    nir = nir_band.astype(float)
    red = red_band.astype(float)

    # Calculate NDVI
    # Add small epsilon to avoid division by zero
    epsilon = 1e-10
    ndvi = (nir - red) / (nir + red + epsilon)

    # Mask invalid values (where both bands are 0)
    mask = (nir == 0) & (red == 0)
    ndvi[mask] = np.nan

    # Clip NDVI to valid range [-1, 1]
    ndvi = np.clip(ndvi, -1, 1)

    # Calculate statistics (ignoring NaN values)
    stats = {
        'mean': float(np.nanmean(ndvi)),
        'min': float(np.nanmin(ndvi)),
        'max': float(np.nanmax(ndvi)),
        'std': float(np.nanstd(ndvi))
    }

    return ndvi, stats


def create_ndvi_visualization(ndvi_array, title='NDVI Visualization'):
    """
    Create a visualization of NDVI data

    Args:
        ndvi_array: NDVI data as numpy array
        title: Plot title

    Returns:
        Base64 encoded PNG image
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    # Create the NDVI plot with RdYlGn colormap (red-yellow-green)
    im = ax.imshow(ndvi_array, cmap='RdYlGn', vmin=-1, vmax=1, interpolation='bilinear')

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
    plt.close()

    return image_base64


def process_sentinel_ndvi(product_path, geojson_polygon):
    """
    Complete processing pipeline for Sentinel-2 NDVI calculation

    Args:
        product_path: Path to downloaded Sentinel-2 product (.zip or .SAFE)
        geojson_polygon: GeoJSON polygon defining the area of interest

    Returns:
        Dictionary with NDVI statistics and visualization
    """
    if not RASTERIO_AVAILABLE:
        raise ImportError("rasterio is required for real NDVI processing. See INSTALL_WINDOWS.md for installation instructions.")

    try:
        # Extract if it's a zip file
        if product_path.endswith('.zip'):
            extract_dir = os.path.dirname(product_path)
            safe_dir = extract_safe_file(product_path, extract_dir)
        else:
            safe_dir = product_path

        # Find band files
        # Band 4 = Red (665 nm), Band 8 = NIR (842 nm) for 10m resolution
        red_band_path = find_band_file(safe_dir, 'B04', '10m')
        nir_band_path = find_band_file(safe_dir, 'B08', '10m')

        print(f"Red band: {red_band_path}")
        print(f"NIR band: {nir_band_path}")

        # Read and clip bands
        red_data = read_and_clip_band(red_band_path, geojson_polygon)
        nir_data = read_and_clip_band(nir_band_path, geojson_polygon)

        # Calculate NDVI
        ndvi_array, stats = calculate_ndvi(nir_data, red_data)

        # Create visualization
        image_base64 = create_ndvi_visualization(ndvi_array)

        return {
            'success': True,
            'ndvi_stats': stats,
            'ndvi_image': image_base64,
            'ndvi_array': ndvi_array  # For further processing if needed
        }

    except Exception as e:
        raise Exception(f"Error processing Sentinel data: {str(e)}")


# Example usage
if __name__ == "__main__":
    # Example: Process a Sentinel-2 product
    # product_path = "path/to/S2A_MSIL2A_20240101T103321_N0510_R108_T32TMT_20240101T134456.zip"
    # geojson_polygon = {...}  # Your GeoJSON polygon
    # result = process_sentinel_ndvi(product_path, geojson_polygon)
    # print(result['ndvi_stats'])
    pass
