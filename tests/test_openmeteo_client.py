import pytest
from unittest.mock import patch

from app.services.openmeteo_client import (
    valider_dates,
    valider_commune,
    recuperer_climat_commune,
)


# -----------------------------
# Tests sur les dates
# -----------------------------

def test_dates_valides():
    valider_dates("2049-01-01", "2049-12-31")


def test_dates_inversees():
    with pytest.raises(
        ValueError,
        match="La date de début doit être antérieure à la date de fin."
    ):
        valider_dates("2050-12-31", "2049-01-01")


def test_dates_hors_periode():
    with pytest.raises(
        ValueError,
        match="La période doit être comprise entre 1950 et 2050."
    ):
        valider_dates("1949-01-01", "1950-01-01")


def test_format_date_invalide():
    with pytest.raises(
        ValueError,
        match="Les dates doivent être au format YYYY-MM-DD."
    ):
        valider_dates("01/01/2049", "31/12/2049")


# -----------------------------
# Tests sur les communes
# -----------------------------

def test_commune_valide():
    commune = valider_commune(13)

    assert commune["nom"] == "Toulouse"
    assert commune["id_commune"] == "13"


def test_commune_inconnue():
    with pytest.raises(
        ValueError,
        match="Commune inconnue."
    ):
        valider_commune(99999)


# -----------------------------
# Vérification : aucun appel API
# si les entrées sont invalides
# -----------------------------

def test_aucun_appel_api_si_commune_inconnue():
    with patch(
        "app.services.openmeteo_client.requests.get"
    ) as mock_get:

        with pytest.raises(ValueError):
            recuperer_climat_commune(
                99999,
                "MRI_AGCM3_2_S",
                "2049-01-01",
                "2049-12-31"
            )

        mock_get.assert_not_called()


def test_aucun_appel_api_si_dates_invalides():
    with patch(
        "app.services.openmeteo_client.requests.get"
    ) as mock_get:

        with pytest.raises(ValueError):
            recuperer_climat_commune(
                13,
                "MRI_AGCM3_2_S",
                "2050-12-31",
                "2049-01-01"
            )

        mock_get.assert_not_called()