from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()

# Gestion des comptes : retrouve l'utilisateur connecté à chaque requête.
login_manager = LoginManager()
# Page vers laquelle @login_required renvoie un visiteur non connecté.
login_manager.login_view = "auth.connexion"
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "warning"