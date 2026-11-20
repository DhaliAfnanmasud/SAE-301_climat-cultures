from flask import render_template
from app.blueprints.auth import auth_bp


@auth_bp.route('/connexion')
def connexion():
    return render_template('auth/connexion.html')


@auth_bp.route('/inscription')
def inscription():
    return render_template('auth/inscription.html')