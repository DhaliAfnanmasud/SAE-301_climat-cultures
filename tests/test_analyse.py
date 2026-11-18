from unittest.mock import MagicMock, patch

from app import create_app
from app.services.apercu import agreger_par_mois

ROUTES = "app.blueprints.analyse.routes"

# Payload simulé (commune 13 = Toulouse), sans appel réel à Open-Meteo.
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

# Fausses lectures de la base (aucune connexion réelle n'est nécessaire).
COMMUNE = {"id_commune": 13, "nom": "Toulouse"}
CULTURE = {"id_culture": 1, "nom": "Maïs grain"}
HORIZON = {"id_temps": 2, "libelle": "2050 (2040–2050)"}


def _fausse_base(culture=CULTURE):
    """Remplace les lectures en base de la route ; culture=None simule
    une culture inconnue."""
    return patch.multiple(
        ROUTES,
        lire_commune=MagicMock(return_value=COMMUNE),
        lire_culture=MagicMock(return_value=culture),
        lire_horizon=MagicMock(return_value=HORIZON),
    )


def _client():
    return create_app().test_client()


def _messages_flash(client):
    """Messages flash en attente dans la session du client de test.

    On ne suit pas les redirections (follow_redirects) : la page du formulaire
    lirait la base de données, ce qui n'a pas de sens dans ces tests.
    """
    with client.session_transaction() as session:
        return [message for _, message in session.get("_flashes", [])]


# --- Route /analyse/resultat -------------------------------------------------

def test_resultat_affiche_le_choix_le_graphique_et_le_placeholder():
    with _fausse_base(), patch(f"{ROUTES}.construire_payload", return_value=PAYLOAD):
        reponse = _client().get(URL)

    page = reponse.get_data(as_text=True)
    assert reponse.status_code == 200
    assert "Toulouse" in page and "Maïs grain" in page
    assert "2050 (2040–2050)" in page
    assert "graphique-climat" in page
    assert "Indicateur : bientôt disponible" in page


def test_parametre_manquant_renvoie_vers_le_formulaire_avec_message():
    client = _client()
    with patch(f"{ROUTES}.construire_payload") as mock_payload:
        reponse = client.get("/analyse/resultat?commune=13")

    assert reponse.status_code == 302
    assert reponse.headers["Location"].endswith("/analyse/")
    assert any("Veuillez choisir une commune" in m for m in _messages_flash(client))
    mock_payload.assert_not_called()


def test_culture_inconnue_refusee_sans_appel_api():
    client = _client()
    with _fausse_base(culture=None), patch(f"{ROUTES}.construire_payload") as mock_payload:
        reponse = client.get("/analyse/resultat?commune=13&culture=99&horizon=2")

    assert reponse.status_code == 302
    assert reponse.headers["Location"].endswith("/analyse/")
    assert "Culture inconnue." in _messages_flash(client)
    mock_payload.assert_not_called()


def test_id_invalide_renvoie_vers_le_formulaire_avec_message():
    client = _client()
    with _fausse_base(), patch(
        f"{ROUTES}.construire_payload", side_effect=ValueError("Commune inconnue.")
    ):
        reponse = client.get(URL)

    assert reponse.status_code == 302
    assert reponse.headers["Location"].endswith("/analyse/")
    assert "Commune inconnue." in _messages_flash(client)


def test_api_indisponible_affiche_un_message_clair():
    with _fausse_base(), patch(
        f"{ROUTES}.construire_payload",
        side_effect=RuntimeError("Le service Open-Meteo est indisponible."),
    ):
        reponse = _client().get(URL)

    assert reponse.status_code == 503
    page = reponse.get_data(as_text=True)
    assert "Le service Open-Meteo est indisponible." in page
    assert "Réessayer" in page


def test_erreur_inattendue_ne_donne_jamais_une_page_500():
    with _fausse_base(), patch(f"{ROUTES}.construire_payload", side_effect=KeyError("bug")):
        reponse = _client().get(URL)

    assert reponse.status_code == 503
    assert "erreur inattendue" in reponse.get_data(as_text=True)


def test_base_injoignable_ne_donne_pas_une_page_500():
    # Si la lecture en base échoue (serveur éteint, .env absent...), la page
    # affiche un message clair au lieu d'une erreur 500.
    with patch(f"{ROUTES}.lire_culture", side_effect=Exception("base injoignable")):
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