from flask import Flask, jsonify, render_template
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html', version=os.getenv('APP_VERSION', 'v1.0'))

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