from flask import Flask, request, send_file, render_template
from flask_cors import CORS
from sentinelhub import SHConfig, BBox, CRS, SentinelHubRequest, DataCollection, MimeType
import numpy as np
from PIL import Image
import io, json
import matplotlib.pyplot as plt
from matplotlib import cm

app = Flask(__name__)
CORS(app)

# --- Load Sentinel Hub credentials ---
with open("sentinel_config.json") as f:
    creds = json.load(f)

config = SHConfig()
config.instance_id = creds["instance_id"]
config.sh_client_id = creds["client_id"]
config.sh_client_secret = creds["client_secret"]

@app.route('/')
def index():
    return render_template('map.html')  # we’ll create this next

@app.route('/ndvi', methods=['POST'])
def get_ndvi():
    data = request.json
    coords = data['coordinates'][0]  # outer polygon ring
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    bbox = BBox(bbox=[min(lons), min(lats), max(lons), max(lats)], crs=CRS.WGS84)

    evalscript = """
    //VERSION=3
    function setup() {
        return { input: ["B04", "B08"], output: { bands: 1 } };
    }
    function evaluatePixel(sample) {
        let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
        return [ndvi];
    }
    """

    request_s2 = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[SentinelHubRequest.input_data(
            data_collection=DataCollection.SENTINEL2_L1C,
            time_interval=("2024-08-01", "2024-08-10")
        )],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=(512, 512),
        config=config
    )

    # --- NDVI processing ---
    ndvi_data = request_s2.get_data()[0].squeeze()
    ndvi = np.clip(ndvi_data, -1, 1)  # limit values

    # ✅ Proper color mapping using matplotlib
    cmap = cm.get_cmap('RdYlGn')  # red → yellow → green
    ndvi_colored = cmap((ndvi + 1) / 2)[:, :, :3]  # drop alpha channel

    # --- Convert to image and send ---
    img = Image.fromarray((ndvi_colored * 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

if __name__ == '__main__':
    app.run(debug=True)
