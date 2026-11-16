from flask import Flask, render_template
from app.config import DevConfig

def create_app(config_class=DevConfig):
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.config.from_object(config_class)

    # Enregistrements des blueprints
    from app.blueprints.main import main_bp
    app.register_blueprint(main_bp)

    from app.blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    from app.blueprints.analyse import analyse_bp
    app.register_blueprint(analyse_bp)

    @app.errorhandler(404)
    def page_introuvable(erreur):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def erreur_serveur(erreur):
        return render_template('errors/500.html'), 500

    return app