# Flask Health Check Application (Broken)
# This fixture has a broken import path

from flask import Flask, jsonify

app = Flask(__name__)

# BUG: Wrong import path - should be from models import HealthStatus
from modeels import HealthStatus

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'message': 'Service is running'
    })

@app.route('/api/status')
def status():
    hs = HealthStatus()
    return jsonify(hs.to_dict())

if __name__ == '__main__':
    app.run(debug=True)
