from flask import jsonify, request, render_template
from app.blueprints.main import main_bp
from app.services.openmeteo_client import recuperer_series_commune


@main_bp.route('/')
def home():
    return render_template('main/index.html')


@main_bp.route('/carte')
def carte():
    return render_template('main/carte.html')


@main_bp.route('/faq')
def faq():
    return render_template('main/faq.html')


@main_bp.route('/contact')
def contact():
    return render_template('main/contact.html')


@main_bp.route('/assistance')
def assistance():
    return render_template('main/assistance.html')


@main_bp.route('/rgpd')
def rgpd():
    return render_template('main/rgpd.html')


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