from app import create_app
from app.models import DimCommune, DimCulture, DimTemps


def _client_sans_csrf():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app, app.test_client()


def _ids_valides(app):
    with app.app_context():
        commune = DimCommune.query.first()
        culture = DimCulture.query.first()
        horizon = DimTemps.query.first()

        return (
            commune.id_commune,
            culture.id_culture,
            horizon.id_temps,
        )


# ------------------------------------------------------------------
# Affichage du formulaire
# ------------------------------------------------------------------

def test_tableau_de_bord_accessible():
    app, client = _client_sans_csrf()

    reponse = client.get("/analyse/")

    assert reponse.status_code == 200
    page = reponse.get_data(as_text=True)

    assert 'name="commune"' in page
    assert 'name="culture"' in page
    assert 'name="horizon"' in page


def test_listes_chargees_depuis_bdd():
    app, client = _client_sans_csrf()

    with app.app_context():
        commune = DimCommune.query.first()
        culture = DimCulture.query.first()
        horizon = DimTemps.query.first()

        nom_commune = commune.nom_commune
        nom_culture = culture.nom_culture
        nom_horizon = horizon.horizon

    reponse = client.get("/analyse/")
    page = reponse.get_data(as_text=True)

    assert nom_commune in page
    assert nom_culture in page
    assert nom_horizon in page


# ------------------------------------------------------------------
# Validation des paramètres
# ------------------------------------------------------------------

def test_champ_manquant_refuse():
    app, client = _client_sans_csrf()

    reponse = client.post(
        "/analyse/",
        data={
            "commune": "13",
            "culture": "1",
        },
        follow_redirects=True,
    )

    assert reponse.status_code == 200
    assert "Tous les champs sont obligatoires." in reponse.get_data(
        as_text=True
    )


def test_id_non_entier_refuse():
    app, client = _client_sans_csrf()

    reponse = client.post(
        "/analyse/",
        data={
            "commune": "abc",
            "culture": "1",
            "horizon": "1",
        },
        follow_redirects=True,
    )

    assert reponse.status_code == 200
    assert "paramètres envoyés sont invalides" in reponse.get_data(
        as_text=True
    )


def test_commune_inexistante_refusee():
    app, client = _client_sans_csrf()

    reponse = client.post(
        "/analyse/",
        data={
            "commune": "99999",
            "culture": "1",
            "horizon": "1",
        },
        follow_redirects=True,
    )

    assert "Commune inconnue." in reponse.get_data(as_text=True)


def test_culture_inexistante_refusee():
    app, client = _client_sans_csrf()

    reponse = client.post(
        "/analyse/",
        data={
            "commune": "13",
            "culture": "99999",
            "horizon": "1",
        },
        follow_redirects=True,
    )

    assert "Culture inconnue." in reponse.get_data(as_text=True)


def test_horizon_inexistant_refuse():
    app, client = _client_sans_csrf()

    reponse = client.post(
        "/analyse/",
        data={
            "commune": "13",
            "culture": "1",
            "horizon": "99999",
        },
        follow_redirects=True,
    )

    assert "Horizon temporel inconnu." in reponse.get_data(as_text=True)


# ------------------------------------------------------------------
# Sélection valide
# ------------------------------------------------------------------

def test_selection_valide_redirige_vers_resultat():
    app, client = _client_sans_csrf()

    id_commune, id_culture, id_temps = _ids_valides(app)

    reponse = client.post(
        "/analyse/",
        data={
            "commune": str(id_commune),
            "culture": str(id_culture),
            "horizon": str(id_temps),
        },
        follow_redirects=False,
    )

    assert reponse.status_code == 302

    location = reponse.headers["Location"]

    assert "/analyse/resultat" in location
    assert f"commune={id_commune}" in location
    assert f"culture={id_culture}" in location
    assert f"horizon={id_temps}" in location


# ------------------------------------------------------------------
# Protection CSRF
# ------------------------------------------------------------------

def test_post_sans_token_csrf_refuse():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = True

    client = app.test_client()

    reponse = client.post(
        "/analyse/",
        data={
            "commune": "13",
            "culture": "1",
            "horizon": "1",
        },
    )

    assert reponse.status_code == 400