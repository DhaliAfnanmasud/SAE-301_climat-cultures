import pytest
from unittest.mock import MagicMock, patch

from app import create_app
from app.services.payload import construire_payload
from app.services.session_id import obtenir_id_session

# Clés conforme au contrat d'interface -----------------------------------
CLES_CONTRAT = {
    "id_commune", "code_insee", "id_culture", "id_temps", "id_modele",
    "id_session", "id_utilisateur", "latitude", "series",
}

# Clés pour les données quotidiennes
CLES_JOUR = {"date", "t_min", "t_max", "t_moy", "precip"}

# Fausses lectures de la base : les tests n'ont besoin ni de réseau ni de base de données. 
# On remplace lire_commune / lire_horizon / lire_modele
# (appelées par payload.py) par ces données.

COMMUNE = {"id_commune": 13, "code_insee": "31555", "nom": "Toulouse",
           "latitude": 43.60, "longitude": 1.44}
HORIZONS = {
    1: {"id_temps": 1, "date_debut": "2015-01-01", "date_fin": "2025-12-31"},
    2: {"id_temps": 2, "date_debut": "2040-01-01", "date_fin": "2050-12-31"},
}
MODELES = {
    1: {"id_modele": 1, "code_api": "MRI_AGCM3_2_S"},
    2: {"id_modele": 2, "code_api": "CMCC_CM2_VHR4"},
}

# Réponse Open-Meteo simulée : 2 jours, avec une valeur manquante (None).
# Les tests n'appellent jamais le vrai service : on remplace recuperer_climat par ce faux résultat grâce à patch().
DAILY = {
    "time": ["2049-01-01", "2049-01-02"],
    "temperature_2m_min": [5.0, None],
    "temperature_2m_max": [12.0, 13.0],
    "temperature_2m_mean": [8.5, 9.5],
    "precipitation_sum": [0.1, 0.0],
} 
# --------------------------------------------------------------------------

def _fausse_base():
    """Remplace les lectures en base par les données ci-dessus."""
    return patch.multiple(
        "app.services.payload",
        lire_commune=MagicMock(side_effect=lambda i: COMMUNE if i == 13 else None),
        lire_horizon=MagicMock(side_effect=HORIZONS.get),
        lire_modele=MagicMock(side_effect=MODELES.get),
    )

def _payload():
    """Construit un payload avec base et Open-Meteo simulés (commune 13)."""
    with _fausse_base(), patch(
        "app.services.payload.recuperer_climat", return_value=DAILY
    ):
        return construire_payload(13, 1, 2, 1, "sess_test")


def test_payload_respecte_le_contrat():
    # Vérifie que les clés du payload sont exactement celles du contrat
    # et que chaque jour de `series` a bien les 5 champs attendus.
    payload = _payload()

    assert set(payload) == CLES_CONTRAT
    assert payload["id_commune"] == 13
    assert payload["code_insee"] == "31555"
    assert payload["latitude"] == 43.60
    assert payload["id_session"] == "sess_test"
    assert payload["id_utilisateur"] is None
    assert all(set(jour) == CLES_JOUR for jour in payload["series"])


def test_deuxieme_modele_et_horizon_de_reference():
    # Horizon 1 -> 2015 à 2025, modèle 2 -> CMCC_CM2_VHR4.
    with _fausse_base(), patch(
        "app.services.payload.recuperer_climat", return_value=DAILY
    ) as mock_climat:
        construire_payload(13, 4, 1, 2, "sess_test")

    mock_climat.assert_called_once_with(
        43.60, 1.44, "CMCC_CM2_VHR4", "2015-01-01", "2025-12-31"
    )


def test_payload_transmet_l_id_utilisateur_du_compte_connecte():
    # Entier pour un compte connecté, None pour un visiteur anonyme.
    with _fausse_base(), patch(
        "app.services.payload.recuperer_climat", return_value=DAILY
    ):
        connecte = construire_payload(13, 1, 2, 1, "sess_test", id_utilisateur=5)
        anonyme = construire_payload(13, 1, 2, 1, "sess_test")

    assert connecte["id_utilisateur"] == 5
    assert anonyme["id_utilisateur"] is None


def test_payload_garde_les_valeurs_manquantes():
    # Une valeur absente chez Open-Meteo doit rester None, pas devenir 0.
    assert _payload()["series"][1]["t_min"] is None


def test_payload_appelle_le_client_avec_les_bons_parametres():
    # Horizon 2 -> 2040 à 2050, modèle 1 -> MRI_AGCM3_2_S, Toulouse (lat/lon).
    with _fausse_base(), patch(
        "app.services.payload.recuperer_climat", return_value=DAILY
    ) as mock_climat:
        construire_payload(13, 1, 2, 1, "sess_test")

    mock_climat.assert_called_once_with(
        43.60, 1.44, "MRI_AGCM3_2_S", "2040-01-01", "2050-12-31"
    )


@pytest.mark.parametrize(
    "args, message",
    [
        ((99999, 1, 2, 1), "Commune inconnue."),
        ((13, 1, 99, 1), "Horizon temporel inconnu."),
        ((13, 1, 2, 99), "Modèle climatique inconnu."),
        (("abc", 1, 2, 1), "id_commune doit être un entier"),
    ],
)
def test_entree_invalide_refusee_sans_appel_api(args, message):
    # Un id inconnu ou non numérique doit lever ValueError AVANT tout appel à l'API pour ne pas gaspiller le quota.
    with _fausse_base(), patch(
        "app.services.payload.recuperer_climat"
    ) as mock_climat:
        with pytest.raises(ValueError, match=message):
            construire_payload(*args, "sess_test")

        mock_climat.assert_not_called()


def test_id_session_cree_puis_conserve():
    # Même visiteur donc même requête, cookie : l'identifiant ne change pas.
    app = create_app()

    with app.test_request_context():
        premier = obtenir_id_session()
        assert premier.startswith("sess_")
        assert obtenir_id_session() == premier


def test_id_session_different_entre_deux_visiteurs():
    # Deux contextes de requête séparés = deux visiteurs = deux identifiants.
    app = create_app()

    with app.test_request_context():
        un = obtenir_id_session()
    with app.test_request_context():
        deux = obtenir_id_session()

    assert un != deux