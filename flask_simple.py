from flask import Flask, send_file
from sentinelhub import SHConfig, BBox, CRS, SentinelHubRequest, DataCollection, MimeType
import numpy as np
from PIL import Image
import io, json

app = Flask(__name__)

# --- Load Sentinel Hub credentials ---
with open("sentinel_config.json") as f:
    creds = json.load(f)

config = SHConfig()
config.instance_id = creds["instance_id"]
config.sh_client_id = creds["client_id"]
config.sh_client_secret = creds["client_secret"]

@app.route('/')
def index():
    return "✅ Sentinel Hub Flask app is running. Go to /ndvi to see the NDVI image."

@app.route('/ndvi')
def get_ndvi_image():
    bbox = BBox(bbox=[2.9, 36.6, 3.2, 36.9], crs=CRS.WGS84)

    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: ["B04", "B08"],
            output: { bands: 1 }
        };
    }

    function evaluatePixel(sample) {
        let ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);
        return [ndvi];
    }
    """

    request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L1C,
                time_interval=("2024-08-01", "2024-08-10")
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=(1024, 1024),
        config=config
    )

    data = request.get_data()[0].squeeze()  # shape (256, 256)
    ndvi_normalized = np.clip((data + 1) / 2, 0, 1)  # scale -1..1 to 0..1
    ndvi_rgb = np.zeros((data.shape[0], data.shape[1], 3))

    # Simple NDVI color mapping: brown to green
    ndvi_rgb[..., 0] = (1 - ndvi_normalized)  # red = low NDVI
    ndvi_rgb[..., 1] = ndvi_normalized        # green = high NDVI

    img = Image.fromarray((ndvi_rgb * 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route('/rgb')
def get_rgb_image():
    bbox = BBox(bbox=[2.9, 36.6, 3.2, 36.9], crs=CRS.WGS84)
    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: ["B04", "B03", "B02"],
            output: { bands: 3 }
        };
    }

    function evaluatePixel(sample) {
        return [sample.B04, sample.B03, sample.B02];
    }
    """
    request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L1C,
                time_interval=("2024-08-01", "2024-08-10")
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=(1024, 1024),
        config=config
    )
    data = request.get_data()[0]
    img = Image.fromarray((np.clip(data * 3, 0, 1) * 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


if __name__ == '__main__':
    app.run(debug=True)
