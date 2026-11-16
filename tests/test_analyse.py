from unittest.mock import patch

from app import create_app
from app.services.apercu import agreger_par_mois

# On simule un payload pour Toulouse (commune 13) sans appel réel à Open-Meteo.
PAYLOAD = {
    "id_commune": 13, "code_insee": "31555", "id_culture": 1, "id_temps": 2,
    "id_modele": 1, "id_session": "sess_test", "id_utilisateur": None,
    "latitude": 43.6,
    "series": [
        {"date": "2049-01-01", "t_min": 2.0, "t_max": 10.0, "t_moy": 6.0, "precip": 1.0},
        {"date": "2049-01-02", "t_min": 4.0, "t_max": 12.0, "t_moy": 8.0, "precip": 2.5},
    ],
}

URL = "/analyse/resultat?commune=13&culture=1&horizon=2"
CIBLE = "app.blueprints.analyse.routes.construire_payload"


def _client():
    return create_app().test_client()


# --- Route /analyse/resultat -------------------------------------------------

def test_resultat_affiche_le_choix_le_graphique_et_le_placeholder():
    with patch(CIBLE, return_value=PAYLOAD):
        reponse = _client().get(URL)

    page = reponse.get_data(as_text=True)
    assert reponse.status_code == 200
    assert "Toulouse" in page and "Maïs grain" in page
    assert "graphique-climat" in page
    assert "Indicateur : bientôt disponible" in page


def test_parametre_manquant_redirige_avec_message():
    with patch(CIBLE) as mock_payload:
        reponse = _client().get("/analyse/resultat?commune=13", follow_redirects=True)

    assert reponse.status_code == 200
    assert "Veuillez choisir une commune" in reponse.get_data(as_text=True)
    mock_payload.assert_not_called()


def test_culture_inconnue_refusee_sans_appel_api():
    with patch(CIBLE) as mock_payload:
        reponse = _client().get(
            "/analyse/resultat?commune=13&culture=99&horizon=2", follow_redirects=True
        )

    assert "Culture inconnue." in reponse.get_data(as_text=True)
    mock_payload.assert_not_called()


def test_id_invalide_affiche_un_message_et_pas_une_erreur():
    with patch(CIBLE, side_effect=ValueError("Commune inconnue.")):
        reponse = _client().get(URL, follow_redirects=True)

    assert reponse.status_code == 200
    assert "Commune inconnue." in reponse.get_data(as_text=True)


def test_api_indisponible_affiche_un_message_clair():
    with patch(CIBLE, side_effect=RuntimeError("Le service Open-Meteo est indisponible.")):
        reponse = _client().get(URL)

    assert reponse.status_code == 503
    page = reponse.get_data(as_text=True)
    assert "Le service Open-Meteo est indisponible." in page
    assert "Réessayer" in page


def test_erreur_inattendue_ne_donne_jamais_une_page_500():
    with patch(CIBLE, side_effect=KeyError("bug")):
        reponse = _client().get(URL)

    assert reponse.status_code == 503
    assert "erreur inattendue" in reponse.get_data(as_text=True)


# --- Agrégation mensuelle ----------------------------------------------------

def test_agregation_moyenne_les_temperatures_et_cumule_la_pluie():
    resultat = agreger_par_mois(PAYLOAD["series"])

    assert resultat["labels"] == ["2049-01"]
    assert resultat["t_moy"] == [7.0]
    assert resultat["t_min"] == [3.0]
    assert resultat["precip"] == [3.5]


def test_agregation_ignore_les_valeurs_manquantes_sans_inventer_de_zero():
    series = [
        {"date": "2049-01-01", "t_min": None, "t_max": 10.0, "t_moy": None, "precip": None},
        {"date": "2049-02-01", "t_min": 1.0, "t_max": 8.0, "t_moy": 4.0, "precip": 0.0},
    ]
    resultat = agreger_par_mois(series)

    assert resultat["labels"] == ["2049-01", "2049-02"]
    assert resultat["t_min"] == [None, 1.0]
    assert resultat["precip"] == [None, 0.0]