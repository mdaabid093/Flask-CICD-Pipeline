from flask import Flask, jsonify, render_template, Response, request, g
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import os
import time

app = Flask(__name__)

REQUEST_COUNT = Counter(
    'flask_request_count', 'Total HTTP requests', ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'flask_request_latency_seconds', 'Request latency', ['endpoint']
)

@app.before_request
def start_timer():
    g.start_time = time.time()

@app.after_request
def record_metrics(response):
    latency = time.time() - g.start_time
    REQUEST_LATENCY.labels(endpoint=request.path).observe(latency)
    REQUEST_COUNT.labels(
        method=request.method, endpoint=request.path, status=response.status_code
    ).inc()
    return response

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route('/')
def home():
    return render_template(
        'index.html',
        version=os.getenv('APP_VERSION', 'v1.0'),
        hostname=os.uname().nodename
    )

@app.route('/health')
def health():
    return jsonify(status="healthy"), 200

@app.route('/api/info')
def info():
    return jsonify({
        "app": "flask-devops-demo",
        "version": os.getenv('APP_VERSION', 'v1.0'),
        "hostname": os.uname().nodename
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)