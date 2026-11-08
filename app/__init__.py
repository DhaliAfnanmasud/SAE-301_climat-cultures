from flask import Flask
from app.config import DevConfig

def create_app(config_class=DevConfig):
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.config.from_object(config_class)

    # Enregistrements des blueprints
    from app.blueprints.main import main_bp
    app.register_blueprint(main_bp)

    return app