from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class Utilisateur(db.Model, UserMixin):
    """Compte utilisateur : correspond à la table `Utilisateur` créée par DATA.

    On ne garde que le strict nécessaire : e-mail, mot de passe haché et consentement. 
    Jamais de mot de passe en clair.
    """

    __tablename__ = "Utilisateur"

    id_utilisateur = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    mot_de_passe_hash = db.Column(db.String(255), nullable=False)
    # Valeur par défaut posée par la base (CURRENT_TIMESTAMP)
    date_creation = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    consentement_rgpd = db.Column(db.Boolean, nullable=False, default=False)
    date_consentement = db.Column(db.DateTime)

    def get_id(self):
        # Flask-Login cherche par défaut un attribut `id` : notre clé primaire s'appelle id_utilisateur
        return str(self.id_utilisateur)

    @staticmethod
    def normaliser_email(email):
        """Espaces retirés et minuscules pour l'email"""
        return (email or "").strip().lower()

    def definir_mot_de_passe(self, mot_de_passe):
        """Stocke uniquement l'empreinte du mot de passe."""
        self.mot_de_passe_hash = generate_password_hash(mot_de_passe)

    def verifier_mot_de_passe(self, mot_de_passe):
        return check_password_hash(self.mot_de_passe_hash, mot_de_passe)

    def donner_consentement(self):
        """Enregistre le consentement RGPD et sa date"""
        self.consentement_rgpd = True
        self.date_consentement = datetime.now(timezone.utc).replace(tzinfo=None)

    def __repr__(self):
        return f"<Utilisateur {self.id_utilisateur}>"


@login_manager.user_loader
def charger_utilisateur(id_utilisateur):
    """Appelée par Flask-Login à chaque requête : retrouve le compte à partir
    de l'identifiant rangé dans la session. 
    Renvoie None si l'id est invalide ou inconnu (le visiteur est alors considéré comme anonyme)."""
    try:
        identifiant = int(id_utilisateur)
    except (TypeError, ValueError):
        return None
    return db.session.get(Utilisateur, identifiant)