from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 👈 allow all devices/browsers to access Flask

coords = {"lat": 0.0, "lon": 0.0}

@app.route('/update', methods=['POST'])
def update():
    global coords
    coords = request.json
    print(f"📍 Updated GPS: {coords}")
    return "OK"

@app.route('/get')
def get():
    return jsonify(coords)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
