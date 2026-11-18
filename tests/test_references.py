import pytest
from flask import Flask

from app.extensions import db
from app.models import DimCommune, DimCulture, DimModele, DimTemps
from app.services.references import (
    lire_commune,
    lire_culture,
    lire_horizon,
    lire_modele,
)


@pytest.fixture
def base_de_test():
    """Petite base SQLite en mémoire remplie de quelques lignes.

    Ces tests n'utilisent ni la base AlwaysData, ni le fichier .env, ni le
    réseau : ils passent sur n'importe quel poste.
    """
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    db.init_app(app)

    with app.app_context():
        db.create_all()
        db.session.add_all([
            DimCommune(id_commune=13, code_insee="31555", nom_commune="Toulouse",
                       latitude=43.60, longitude=1.44),
            DimCulture(id_culture=1, nom_culture="Maïs grain",
                       temperature_base=8.0, seuil_gel=-2.0),
            DimTemps(id_temps=2, horizon="2050", annee_debut=2040, annee_fin=2050),
            DimModele(id_modele=1, code_api="MRI_AGCM3_2_S"),
        ])
        db.session.commit()
        yield
        db.session.remove()
        db.drop_all()


def test_lire_commune_renvoie_des_flottants(base_de_test):
    commune = lire_commune(13)

    assert commune["nom"] == "Toulouse"
    assert commune["code_insee"] == "31555"
    assert isinstance(commune["latitude"], float)
    assert commune["latitude"] == 43.6


def test_lire_commune_accepte_un_id_texte(base_de_test):
    # Les ids viennent de l'URL, donc sous forme de texte.
    assert lire_commune("13")["nom"] == "Toulouse"


def test_ids_inconnus_ou_invalides_renvoient_none(base_de_test):
    assert lire_commune(99999) is None
    assert lire_commune("abc") is None
    assert lire_commune(None) is None
    assert lire_culture(99999) is None
    assert lire_horizon(99999) is None
    assert lire_modele(99999) is None


def test_lire_horizon_reconstruit_les_dates(base_de_test):
    horizon = lire_horizon(2)

    assert horizon["date_debut"] == "2040-01-01"
    assert horizon["date_fin"] == "2050-12-31"
    assert horizon["libelle"] == "2050 (2040–2050)"


def test_lire_culture_et_modele(base_de_test):
    assert lire_culture(1)["nom"] == "Maïs grain"
    assert lire_modele(1)["code_api"] == "MRI_AGCM3_2_S"