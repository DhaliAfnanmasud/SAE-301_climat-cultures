import pytest
from flask import Flask
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Utilisateur
from app.models.utilisateur import charger_utilisateur


@pytest.fixture
def base_de_test():
    """Base SQLite en mémoire : aucun accès à la base AlwaysData, aucun
    vrai compte créé."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def _utilisateur(email="alice@exemple.fr", mot_de_passe="Motdepasse123"):
    utilisateur = Utilisateur(email=email)
    utilisateur.definir_mot_de_passe(mot_de_passe)
    return utilisateur


# --- Mot de passe ---------------------------------------------------------------

def test_le_mot_de_passe_n_est_jamais_stocke_en_clair():
    utilisateur = _utilisateur(mot_de_passe="Motdepasse123")

    assert utilisateur.mot_de_passe_hash != "Motdepasse123"
    assert "Motdepasse123" not in utilisateur.mot_de_passe_hash


def test_le_hash_tient_dans_la_colonne_de_la_base():
    # La colonne mot_de_passe_hash fait 255 caractères (schéma de DATA).
    assert len(_utilisateur().mot_de_passe_hash) <= 255


def test_bon_et_mauvais_mot_de_passe():
    utilisateur = _utilisateur(mot_de_passe="Motdepasse123")

    assert utilisateur.verifier_mot_de_passe("Motdepasse123") is True
    assert utilisateur.verifier_mot_de_passe("autre-chose") is False


def test_deux_comptes_au_meme_mot_de_passe_ont_des_hash_differents():
    # Le hash est « salé » : un hash volé ne trahit pas les mots de passe identiques.
    un = _utilisateur(email="un@exemple.fr")
    deux = _utilisateur(email="deux@exemple.fr")

    assert un.mot_de_passe_hash != deux.mot_de_passe_hash


# --- Fonctions utilitaires ------------------------------------------------------

def test_normaliser_email():
    assert Utilisateur.normaliser_email("  Alice@Exemple.FR ") == "alice@exemple.fr"
    assert Utilisateur.normaliser_email(None) == ""


def test_donner_consentement_enregistre_la_date():
    utilisateur = _utilisateur()
    assert not utilisateur.consentement_rgpd

    utilisateur.donner_consentement()

    assert utilisateur.consentement_rgpd is True
    assert utilisateur.date_consentement is not None


def test_get_id_est_un_texte():
    # Flask-Login range l'identifiant dans la session sous forme de texte.
    utilisateur = Utilisateur(id_utilisateur=7)

    assert utilisateur.get_id() == "7"


# --- Avec une base (SQLite en mémoire) -------------------------------------------

def test_creation_avec_valeurs_par_defaut(base_de_test):
    utilisateur = _utilisateur()
    db.session.add(utilisateur)
    db.session.commit()

    assert utilisateur.id_utilisateur is not None
    assert utilisateur.consentement_rgpd is False
    assert utilisateur.date_creation is not None


def test_deux_comptes_avec_le_meme_email_sont_refuses(base_de_test):
    db.session.add(_utilisateur(email="alice@exemple.fr"))
    db.session.commit()

    db.session.add(_utilisateur(email="alice@exemple.fr"))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_charger_utilisateur(base_de_test):
    utilisateur = _utilisateur()
    db.session.add(utilisateur)
    db.session.commit()

    assert charger_utilisateur(utilisateur.get_id()).email == "alice@exemple.fr"
    assert charger_utilisateur("99999") is None
    assert charger_utilisateur("abc") is None
    assert charger_utilisateur(None) is None