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

# Résultat simulé de calculer_indicateurs (module de DATA).
INDICATEURS = {
    "id_commune": 13, "id_culture": 1, "id_temps": 2, "id_modele": 1,
    "id_session": "sess_test", "id_utilisateur": None,
    "jours_gel": 2.5, "gdd": 3300.0, "jours_stress_thermique": 10.0,
    "bilan_hydrique_mm": -150.3, "id_verdict": 1, "verdict": "viable",
    "nb_annees": 11, "nb_annees_incompletes": 0,
    "serie_incomplete": False, "nb_jours_ignores": 0,
}
CALCUL = f"{ROUTES}.calculer_indicateurs"

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

def test_resultat_affiche_le_choix_le_graphique_et_les_indicateurs():
    with _fausse_base(), patch(
        f"{ROUTES}.construire_payload", return_value=PAYLOAD
    ), patch(CALCUL, return_value=INDICATEURS):
        reponse = _client().get(URL)

    page = reponse.get_data(as_text=True)
    assert reponse.status_code == 200
    assert "Toulouse" in page and "Maïs grain" in page
    assert "2050 (2040–2050)" in page
    assert "graphique-climat" in page
    # Indicateurs avec virgule décimale française, et verdict
    assert "2,5" in page and "3300,0" in page and "-150,3" in page
    assert "Verdict : Viable" in page and "alert-success" in page
    assert "bientôt disponible" not in page


def test_bilan_hydrique_absent_affiche_non_disponible():
    sans_bilan = {**INDICATEURS, "bilan_hydrique_mm": None}
    with _fausse_base(), patch(
        f"{ROUTES}.construire_payload", return_value=PAYLOAD
    ), patch(CALCUL, return_value=sans_bilan):
        page = _client().get(URL).get_data(as_text=True)

    assert "Non disponible" in page


def test_verdicts_menacee_et_non_viable_ont_leur_couleur():
    for id_verdict, libelle, classe in ((2, "Menacée", "alert-warning"),
                                        (3, "Non viable", "alert-danger")):
        resultat = {**INDICATEURS, "id_verdict": id_verdict}
        with _fausse_base(), patch(
            f"{ROUTES}.construire_payload", return_value=PAYLOAD
        ), patch(CALCUL, return_value=resultat):
            page = _client().get(URL).get_data(as_text=True)

        assert f"Verdict : {libelle}" in page and classe in page


def test_serie_incomplete_affiche_un_avertissement():
    incomplet = {**INDICATEURS, "serie_incomplete": True, "nb_annees": 1}
    with _fausse_base(), patch(
        f"{ROUTES}.construire_payload", return_value=PAYLOAD
    ), patch(CALCUL, return_value=incomplet):
        page = _client().get(URL).get_data(as_text=True)

    assert "Série incomplète" in page


def test_chaine_complete_avec_le_vrai_module_de_calcul():
    # Deux journées situées dans la saison de culture du maïs
    payload_saison = {
        **PAYLOAD,
        "series": [
            {
                **PAYLOAD["series"][0],
                "date": "2049-05-01"
            },
            {
                **PAYLOAD["series"][1],
                "date": "2049-05-02"
            },
        ],
    }

    with _fausse_base(), patch(
        f"{ROUTES}.construire_payload",
        return_value=payload_saison
    ):
        reponse = _client().get(URL)

    page = reponse.get_data(as_text=True)

    assert reponse.status_code == 200
    assert "Série incomplète" in page
    assert "Verdict : Non viable" in page


def test_calcul_refuse_affiche_une_page_derreur_claire():
    with _fausse_base(), patch(
        f"{ROUTES}.construire_payload", return_value=PAYLOAD
    ), patch(CALCUL, side_effect=ValueError("aucun jour exploitable")):
        reponse = _client().get(URL)

    assert reponse.status_code == 503
    assert "insuffisantes" in reponse.get_data(as_text=True)


def test_erreur_inattendue_du_calcul_ne_donne_pas_une_page_500():
    with _fausse_base(), patch(
        f"{ROUTES}.construire_payload", return_value=PAYLOAD
    ), patch(CALCUL, side_effect=KeyError("bug")):
        reponse = _client().get(URL)

    assert reponse.status_code == 503
    assert "erreur inattendue" in reponse.get_data(as_text=True)


# --- Écriture dans Fact_Indicateur (ENREGISTRER_FACT) -------------------------

def test_aucune_ecriture_en_base_par_defaut(monkeypatch):
    monkeypatch.delenv("ENREGISTRER_FACT", raising=False)
    with _fausse_base(), patch(
        f"{ROUTES}.construire_payload", return_value=PAYLOAD
    ), patch(CALCUL, return_value=INDICATEURS), patch(
        f"{ROUTES}.ecrire_fact"
    ) as mock_ecrire:
        reponse = _client().get(URL)

    assert reponse.status_code == 200
    mock_ecrire.assert_not_called()


def test_ecriture_activee_par_ENREGISTRER_FACT(monkeypatch):
    monkeypatch.setenv("ENREGISTRER_FACT", "1")
    connexion = MagicMock()
    with _fausse_base(), patch(
        f"{ROUTES}.construire_payload", return_value=PAYLOAD
    ), patch(CALCUL, return_value=INDICATEURS), patch(
        f"{ROUTES}.ecrire_fact"
    ) as mock_ecrire, patch(
        f"{ROUTES}.db"
    ) as mock_db:
        mock_db.engine.raw_connection.return_value = connexion
        reponse = _client().get(URL)

    assert reponse.status_code == 200
    mock_ecrire.assert_called_once_with(connexion, INDICATEURS)
    connexion.close.assert_called_once()


def test_echec_decriture_nempeche_pas_laffichage(monkeypatch):
    monkeypatch.setenv("ENREGISTRER_FACT", "1")
    with _fausse_base(), patch(
        f"{ROUTES}.construire_payload", return_value=PAYLOAD
    ), patch(CALCUL, return_value=INDICATEURS), patch(
        f"{ROUTES}.ecrire_fact", side_effect=Exception("base injoignable")
    ), patch(f"{ROUTES}.db"):
        reponse = _client().get(URL)

    assert reponse.status_code == 200
    assert "Verdict : Viable" in reponse.get_data(as_text=True)


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
    ), patch(CALCUL) as mock_calcul:
        reponse = _client().get(URL)

    assert reponse.status_code == 503

    page = reponse.get_data(as_text=True)

    assert "Le service Open-Meteo est indisponible." in page
    assert "Réessayer" in page
    assert "alert-danger" in page
    assert "graphique-climat" not in page

    mock_calcul.assert_not_called()


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


# --- Appel du calcul, mentions obligatoires, aucune écriture en cas d'erreur ----

def test_la_route_appelle_le_calcul_avec_le_payload():
    with _fausse_base(), patch(
        f"{ROUTES}.construire_payload", return_value=PAYLOAD
    ), patch(CALCUL, return_value=INDICATEURS) as mock_calcul:
        _client().get(URL)

    mock_calcul.assert_called_once_with(PAYLOAD)


def test_indicateurs_avant_le_graphique_avec_nuance_et_source():
    with _fausse_base(), patch(
        f"{ROUTES}.construire_payload", return_value=PAYLOAD
    ), patch(CALCUL, return_value=INDICATEURS):
        page = _client().get(URL).get_data(as_text=True)

    # Normalisation des espaces et des retours à la ligne
    page = " ".join(page.split())

    assert page.index("Indicateurs agroclimatiques") < page.index("graphique-climat")
    assert "à interpréter comme une tendance" in page
    assert "Calcul des indicateurs sur la saison de culture" in page
    assert "CC BY 4.0" in page


def test_rien_nest_ecrit_en_base_en_cas_derreur(monkeypatch):
    # Même avec l'écriture activée, aucune erreur (API, id invalide, calcul)
    # ne doit laisser une ligne dans Fact_Indicateur.
    monkeypatch.setenv("ENREGISTRER_FACT", "1")
    scenarios = [
        {"payload": RuntimeError("API indisponible"), "calcul": INDICATEURS},
        {"payload": ValueError("Commune inconnue."), "calcul": INDICATEURS},
        {"payload": PAYLOAD, "calcul": ValueError("aucun jour exploitable")},
        {"payload": PAYLOAD, "calcul": KeyError("bug")},
    ]
    for scenario in scenarios:
        kwargs_payload = (
            {"side_effect": scenario["payload"]}
            if isinstance(scenario["payload"], Exception)
            else {"return_value": scenario["payload"]}
        )
        kwargs_calcul = (
            {"side_effect": scenario["calcul"]}
            if isinstance(scenario["calcul"], Exception)
            else {"return_value": scenario["calcul"]}
        )
        with _fausse_base(), patch(
            f"{ROUTES}.construire_payload", **kwargs_payload
        ), patch(CALCUL, **kwargs_calcul), patch(
            f"{ROUTES}.ecrire_fact"
        ) as mock_ecrire, patch(f"{ROUTES}.db"):
            _client().get(URL)

        mock_ecrire.assert_not_called()