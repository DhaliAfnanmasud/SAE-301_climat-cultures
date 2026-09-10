from flask import jsonify
from app.blueprints.main import main_bp

@main_bp.route('/')
def home():
    return "<h1>Hello World !</h1>"

@main_bp.route('/api/health')
def health():
    return jsonify({"status": "ok", "message": "API operationnelle"})

