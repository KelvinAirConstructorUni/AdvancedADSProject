from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os

# Configure static folder to serve the web viewer
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, 'web')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/web')
CORS(app)  # 👈 allow all devices/browsers to access Flask

coords = {"lat": 0.0, "lon": 0.0}

@app.route('/update', methods=['POST'])
def update():  # backward-compatible endpoint
    global coords
    coords = request.get_json(force=True) or coords
    print(f"📍 Updated GPS: {coords}")
    return "OK"

@app.route('/get')
def get():
    return jsonify(coords)

# New normalized API endpoints
@app.post('/api/gps')
def api_update_gps():
    global coords
    coords = request.get_json(force=True) or coords
    print(f"📍 Updated GPS (api): {coords}")
    return "OK"

@app.get('/api/gps')
def api_get_gps():
    return jsonify(coords)

@app.get('/')
def root():
    # Serve the web viewer if present
    if os.path.isfile(os.path.join(STATIC_DIR, 'index.html')):
        return send_from_directory(STATIC_DIR, 'index.html')
    return "Web viewer not found. Ensure the 'web/index.html' exists."

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
