import pytest
from unittest.mock import patch, Mock
from app.services.openmeteo_client import (
    valider_dates,
    valider_commune,
    recuperer_climat_commune,
    recuperer_climat,
    transformer_reponse,
    recuperer_series_commune
)
from requests.exceptions import Timeout
from app.services.cache import generer_cle_cache


def test_format_contrat_dev_data():
    daily = {
        "time": ["2049-01-01"],
        "temperature_2m_min": [5.0],
        "temperature_2m_max": [12.0],
        "temperature_2m_mean": [8.5],
        "precipitation_sum": [0.1],
    }

    with patch(
        "app.services.openmeteo_client.recuperer_climat",
        return_value=daily
    ):
        resultat = recuperer_series_commune(
            13,
            "MRI_AGCM3_2_S",
            "2049-01-01",
            "2049-12-31"
        )

    assert "id_commune" in resultat
    assert "series" in resultat

    assert resultat["series"][0] == {
        "date": "2049-01-01",
        "t_min": 5.0,
        "t_max": 12.0,
        "t_moy": 8.5,
        "precip": 0.1,
    }

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


# -----------------------------
# Tests des erreurs de l'API
# -----------------------------

def test_reponse_vide():
    mock_reponse = Mock()
    mock_reponse.status_code = 200
    mock_reponse.json.return_value = {}

    with patch(
        "app.services.openmeteo_client.lire_cache",
        return_value=None
    ), patch(
        "app.services.openmeteo_client.requests.get",
        return_value=mock_reponse
    ) as mock_get:

        with pytest.raises(
            RuntimeError,
            match="Données indisponibles pour ce modèle"
        ):
            recuperer_climat(
                43.60,
                1.44,
                "MRI_AGCM3_2_S",
                "2049-01-01",
                "2049-12-31"
            )

        assert mock_get.call_count == 1


def test_erreur_500_trois_tentatives():
    mock_reponse = Mock()
    mock_reponse.status_code = 500

    with patch(
        "app.services.openmeteo_client.lire_cache",
        return_value=None
    ), patch(
        "app.services.openmeteo_client.requests.get",
        return_value=mock_reponse
    ) as mock_get, patch(
        "app.services.openmeteo_client.time.sleep"
    ):

        with pytest.raises(
            RuntimeError,
            match="Service indisponible"
        ):
            recuperer_climat(
                43.60,
                1.44,
                "MRI_AGCM3_2_S",
                "2049-01-01",
                "2049-12-31"
            )

        assert mock_get.call_count == 3


def test_erreur_429_quota_journalier():
    mock_reponse = Mock()
    mock_reponse.status_code = 429
    mock_reponse.text = "Daily API request limit exceeded"

    with patch(
        "app.services.openmeteo_client.lire_cache",
        return_value=None
    ), patch(
        "app.services.openmeteo_client.requests.get",
        return_value=mock_reponse
    ) as mock_get:

        with pytest.raises(
            RuntimeError,
            match="Quota journalier dépassé"
        ):
            recuperer_climat(
                43.60,
                1.44,
                "MRI_AGCM3_2_S",
                "2049-01-01",
                "2049-12-31"
            )

        assert mock_get.call_count == 1


def test_erreur_429_saturation_un_seul_reessai():
    mock_reponse = Mock()
    mock_reponse.status_code = 429
    mock_reponse.text = "Too many requests"

    with patch(
        "app.services.openmeteo_client.lire_cache",
        return_value=None
    ), patch(
        "app.services.openmeteo_client.requests.get",
        return_value=mock_reponse
    ) as mock_get, patch(
        "app.services.openmeteo_client.time.sleep"
    ):

        with pytest.raises(
            RuntimeError,
            match="Service saturé"
        ):
            recuperer_climat(
                43.60,
                1.44,
                "MRI_AGCM3_2_S",
                "2049-01-01",
                "2049-12-31"
            )

        assert mock_get.call_count == 2


def test_timeout_trois_tentatives():
    with patch(
        "app.services.openmeteo_client.lire_cache",
        return_value=None
    ), patch(
        "app.services.openmeteo_client.requests.get",
        side_effect=Timeout
    ) as mock_get, patch(
        "app.services.openmeteo_client.time.sleep"
    ):

        with pytest.raises(
            RuntimeError,
            match="Service indisponible"
        ):
            recuperer_climat(
                43.60,
                1.44,
                "MRI_AGCM3_2_S",
                "2049-01-01",
                "2049-12-31"
            )

        assert mock_get.call_count == 3


# -----------------------------
# Tests réponse valide / format
# -----------------------------

def test_requete_valide():
    daily = {
        "time": ["2049-01-01", "2049-01-02"],
        "temperature_2m_min": [5.0, 6.0],
        "temperature_2m_max": [12.0, 13.0],
        "temperature_2m_mean": [8.5, 9.5],
        "precipitation_sum": [0.1, 0.0],
    }

    mock_reponse = Mock()
    mock_reponse.status_code = 200
    mock_reponse.json.return_value = {"daily": daily}

    with patch(
        "app.services.openmeteo_client.lire_cache",
        return_value=None
    ), patch(
        "app.services.openmeteo_client.requests.get",
        return_value=mock_reponse
    ) as mock_get, patch(
        "app.services.openmeteo_client.ecrire_cache"
    ) as mock_cache:

        resultat = recuperer_climat(
            43.60,
            1.44,
            "MRI_AGCM3_2_S",
            "2049-01-01",
            "2049-12-31"
        )

        assert resultat == daily
        assert mock_get.call_count == 1
        mock_cache.assert_called_once()


def test_transformation_reponse():
    daily = {
        "time": ["2049-01-01", "2049-01-02"],
        "temperature_2m_min": [5.0, 6.0],
        "temperature_2m_max": [12.0, 13.0],
        "temperature_2m_mean": [8.5, 9.5],
        "precipitation_sum": [0.1, 0.0],
    }

    resultat = transformer_reponse(daily)

    assert resultat == [
        {
            "date": "2049-01-01",
            "t_min": 5.0,
            "t_max": 12.0,
            "t_moy": 8.5,
            "precip": 0.1,
        },
        {
            "date": "2049-01-02",
            "t_min": 6.0,
            "t_max": 13.0,
            "t_moy": 9.5,
            "precip": 0.0,
        },
    ]


def test_valeur_manquante_reste_none():
    daily = {
        "time": ["2049-01-01"],
        "temperature_2m_min": [None],
        "temperature_2m_max": [12.0],
        "temperature_2m_mean": [8.5],
        "precipitation_sum": [None],
    }

    resultat = transformer_reponse(daily)

    assert resultat[0]["t_min"] is None
    assert resultat[0]["precip"] is None
    assert resultat[0]["t_max"] == 12.0


# -----------------------------
# Tests du cache
# -----------------------------

def test_cache_existant_evite_appel_api():
    donnees_cache = {
        "time": ["2049-01-01"],
        "temperature_2m_min": [5.0],
        "temperature_2m_max": [12.0],
        "temperature_2m_mean": [8.5],
        "precipitation_sum": [0.1],
    }

    with patch(
        "app.services.openmeteo_client.lire_cache",
        return_value=donnees_cache
    ), patch(
        "app.services.openmeteo_client.requests.get"
    ) as mock_get:

        resultat = recuperer_climat(
            43.60,
            1.44,
            "MRI_AGCM3_2_S",
            "2049-01-01",
            "2049-12-31"
        )

        assert resultat == donnees_cache
        mock_get.assert_not_called()


def test_erreur_api_non_enregistree_dans_cache():
    mock_reponse = Mock()
    mock_reponse.status_code = 500

    with patch(
        "app.services.openmeteo_client.lire_cache",
        return_value=None
    ), patch(
        "app.services.openmeteo_client.requests.get",
        return_value=mock_reponse
    ), patch(
        "app.services.openmeteo_client.ecrire_cache"
    ) as mock_cache, patch(
        "app.services.openmeteo_client.time.sleep"
    ):

        with pytest.raises(RuntimeError):
            recuperer_climat(
                43.60,
                1.44,
                "MRI_AGCM3_2_S",
                "2049-01-01",
                "2049-12-31"
            )

        mock_cache.assert_not_called()


def test_cle_cache_identique_pour_memes_parametres():
    parametres_1 = {
        "latitude": 43.60,
        "longitude": 1.44,
        "models": "MRI_AGCM3_2_S",
        "start_date": "2049-01-01",
    }

    parametres_2 = {
        "start_date": "2049-01-01",
        "models": "MRI_AGCM3_2_S",
        "longitude": 1.44,
        "latitude": 43.60,
    }

    assert generer_cle_cache(parametres_1) == generer_cle_cache(parametres_2)


def test_cle_cache_change_si_parametre_change():
    parametres_1 = {
        "latitude": 43.60,
        "longitude": 1.44,
        "models": "MRI_AGCM3_2_S",
    }

    parametres_2 = {
        "latitude": 43.60,
        "longitude": 1.44,
        "models": "CMCC_CM2_VHR4",
    }

    assert generer_cle_cache(parametres_1) != generer_cle_cache(parametres_2)


# -----------------------------
# Tests des fonctionnalités encore manquantes
# -----------------------------

@pytest.mark.xfail(
    reason="La validation du modèle n'est pas encore implémentée",
    strict=True
)
def test_modele_inconnu_refuse_avant_appel_api():
    with patch(
        "app.services.openmeteo_client.requests.get"
    ) as mock_get:

        with pytest.raises(ValueError):
            recuperer_climat_commune(
                13,
                "MODELE_INCONNU",
                "2049-01-01",
                "2049-12-31"
            )

        mock_get.assert_not_called()