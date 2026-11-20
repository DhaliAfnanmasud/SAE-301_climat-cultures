from flask import Blueprint

# Blueprint des pages d'analyse (sélection -> résultat). 
# Toutes les routes commencent par /analyse. Il est enregistré dans app/__init__.py.
analyse_bp = Blueprint('analyse', __name__, url_prefix='/analyse')

from app.blueprints.analyse import routes  # noqa: E402,F401