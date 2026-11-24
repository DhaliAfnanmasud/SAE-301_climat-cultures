import pytest
from unittest.mock import patch

from app import create_app
from app.extensions import db
from app.models import DimModele
from app.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture
def client():
    app = create_app(TestConfig)

    with app.app_context():
        DimModele.__table__.create(db.engine)

        db.session.add(
            DimModele(
                id_modele=1,
                code_api="MRI_AGCM3_2_S"
            )
        )
        db.session.commit()

    return app.test_client()


def test_modele_inconnu_refuse_sans_appel_api(client):
    with patch(
        "app.blueprints.main.routes.recuperer_series_commune"
    ) as mock_api:

        reponse = client.get(
            "/api/indicateurs",
            query_string={
                "commune": "13",
                "modele": "FAUX_MODELE",
                "date_debut": "2049-01-01",
                "date_fin": "2049-12-31"
            }
        )

        assert reponse.status_code == 400
        assert reponse.get_json()["erreur"] == "Modèle climatique inconnu."
        mock_api.assert_not_called()


def test_modele_valide_accepte(client):
    with patch(
        "app.blueprints.main.routes.recuperer_series_commune",
        return_value={"series": []}
    ) as mock_api:

        reponse = client.get(
            "/api/indicateurs",
            query_string={
                "commune": "13",
                "modele": "MRI_AGCM3_2_S",
                "date_debut": "2049-01-01",
                "date_fin": "2049-12-31"
            }
        )

        assert reponse.status_code == 200

        mock_api.assert_called_once_with(
            "13",
            "MRI_AGCM3_2_S",
            "2049-01-01",
            "2049-12-31"
        )