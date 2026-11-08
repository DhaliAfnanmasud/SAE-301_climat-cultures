from flask import jsonify, request
from app.blueprints.main import main_bp
from app.services.openmeteo_client import recuperer_series_commune

@main_bp.route('/')
def home():
    return "<h1>Hello World !</h1>"

@main_bp.route('/api/health')
def health():
    return jsonify({"status": "ok", "message": "API operationnelle"})

@main_bp.route('/api/indicateurs')
def indicateurs():
    commune = request.args.get("commune")
    modele = request.args.get("modele")
    date_debut = request.args.get("date_debut")
    date_fin = request.args.get("date_fin")

    if not commune or not modele or not date_debut or not date_fin:
        return jsonify({
            "erreur": "Paramètres manquants : commune, modele, date_debut et date_fin sont obligatoires."
        }), 400

    try:
        resultat = recuperer_series_commune(commune, modele, date_debut, date_fin)
    except ValueError as erreur:
        return jsonify({"erreur": str(erreur)}), 400
    except RuntimeError as erreur:
        return jsonify({"erreur": str(erreur)}), 503

    return jsonify(resultat)