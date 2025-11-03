# Windows Installation Guide

## Issue with Rasterio on Windows

Rasterio requires GDAL, which is difficult to install on Windows. Here are multiple solutions:

## Solution 1: Install Basic Dependencies First (Recommended for Testing)

Install everything except rasterio to test the application with mock data:

```bash
pip install -r requirements.txt
```

The app will work with **demo/mock NDVI data** for testing the interface.

## Solution 2: Install Rasterio with Pre-built Wheels

### Option A: Use Conda (Easiest)
If you have Anaconda or Miniconda:

```bash
conda install -c conda-forge rasterio
```

### Option B: Use pip with unofficial wheels
Download pre-built wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#rasterio

Then install:
```bash
pip install path\to\downloaded\rasterio-xxx.whl
```

### Option C: Use latest rasterio (may have Windows wheels)
```bash
pip install rasterio --no-binary rasterio
```

Or try the latest version:
```bash
pip install rasterio
```

## Solution 3: Use OSGeo4W (Full GDAL Stack)

1. Download OSGeo4W installer from: https://trac.osgeo.org/osgeo4w/
2. Install GDAL and Python bindings
3. Then install rasterio

## Solution 4: Use Docker (Advanced)

Run the application in a Docker container where GDAL is pre-installed.

## Quick Test Without Rasterio

You can test the application interface without rasterio. The app will:
- ✓ Display the interactive map
- ✓ Allow drawing polygons
- ✓ Query Sentinel-2 data
- ✓ Show mock NDVI results
- ✗ Cannot process real satellite imagery (falls back to demo data)

To test, just run:
```bash
python app.py
```

The app will show warnings but will work with demo data!

## Verify Installation

To check what's installed:
```bash
pip list | findstr "rasterio"
```

## Need Help?

If you're still having issues, let me know which solution you'd like to try!
