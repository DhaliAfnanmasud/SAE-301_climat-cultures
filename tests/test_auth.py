import pytest

from app import create_app
from app.config import DevConfig
from app.extensions import db
from app.models import Utilisateur

EMAIL = "alice@exemple.fr"
MOT_DE_PASSE = "Motdepasse123"


class ConfigTest(DevConfig):
    """Base SQLite en mémoire : aucun accès à la base AlwaysData, aucun vrai compte créé."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ConfigTestAvecCsrf(ConfigTest):
    WTF_CSRF_ENABLED = True


@pytest.fixture
def client():
    app = create_app(ConfigTest)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def _inscrire(client, email=EMAIL, mot_de_passe=MOT_DE_PASSE, consentement=True):
    donnees = {"email": email, "mot_de_passe": mot_de_passe}
    if consentement:
        donnees["consentement"] = "on"
    return client.post("/compte/inscription", data=donnees)


def _connecter(client, email=EMAIL, mot_de_passe=MOT_DE_PASSE, adresse="/compte/connexion"):
    return client.post(adresse, data={"email": email, "mot_de_passe": mot_de_passe})


def _nombre_de_comptes():
    return db.session.scalar(db.select(db.func.count()).select_from(Utilisateur))


def _est_connecte(client):
    with client.session_transaction() as session:
        return "_user_id" in session


# --- Inscription -------------------------------------------------------------------

def test_inscription_valide_cree_un_compte_au_mot_de_passe_hache(client):
    reponse = _inscrire(client, email="  Alice@Exemple.FR ")

    assert reponse.status_code == 302
    assert reponse.headers["Location"].endswith("/compte/connexion")
    utilisateur = db.session.execute(db.select(Utilisateur)).scalar_one()
    assert utilisateur.email == "alice@exemple.fr"
    assert utilisateur.mot_de_passe_hash != MOT_DE_PASSE
    assert utilisateur.consentement_rgpd is True
    assert utilisateur.date_consentement is not None


@pytest.mark.parametrize(
    "donnees, message",
    [
        ({"email": "pas-un-email", "mot_de_passe": MOT_DE_PASSE, "consentement": "on"}, "pas valide"),
        ({"email": EMAIL, "mot_de_passe": "court", "consentement": "on"}, "au moins 8 caractères"),
        ({"email": EMAIL, "mot_de_passe": MOT_DE_PASSE}, "accepter les conditions"),
    ],
)
def test_inscription_invalide_refusee_avec_message(client, donnees, message):
    reponse = client.post("/compte/inscription", data=donnees)

    assert reponse.status_code == 200
    assert message in reponse.get_data(as_text=True)
    assert _nombre_de_comptes() == 0


def test_inscription_email_deja_utilise_refusee_meme_en_majuscules(client):
    _inscrire(client)

    reponse = _inscrire(client, email="ALICE@exemple.fr")

    assert reponse.status_code == 200
    assert "Impossible de créer un compte" in reponse.get_data(as_text=True)
    assert _nombre_de_comptes() == 1


def test_le_mot_de_passe_n_est_jamais_renvoye_dans_la_page(client):
    reponse = _inscrire(client, mot_de_passe="court")

    assert "court" not in reponse.get_data(as_text=True).replace("au moins 8 caractères", "")


# --- Connexion -----------------------------------------------------------------------

def test_connexion_reussie(client):
    _inscrire(client)

    reponse = _connecter(client)

    assert reponse.status_code == 302
    assert reponse.headers["Location"].endswith("/analyse/")
    assert _est_connecte(client)


def test_connexion_renouvelle_l_id_session(client):
    _inscrire(client)
    with client.session_transaction() as session:
        session["id_session"] = "sess_ancien_visiteur"

    _connecter(client)

    with client.session_transaction() as session:
        assert session.get("id_session") != "sess_ancien_visiteur"


def test_echec_de_connexion_donne_le_meme_message_dans_les_deux_cas(client):
    _inscrire(client)

    mauvais_mot_de_passe = _connecter(client, mot_de_passe="Mauvais123456")
    email_inconnu = _connecter(client, email="inconnu@exemple.fr")

    for reponse in (mauvais_mot_de_passe, email_inconnu):
        assert reponse.status_code == 200
        assert "E-mail ou mot de passe incorrect." in reponse.get_data(as_text=True)
    assert not _est_connecte(client)


def test_destination_next_interne_respectee(client):
    _inscrire(client)

    reponse = _connecter(client, adresse="/compte/connexion?next=/compte/mon-compte")

    assert reponse.headers["Location"].endswith("/compte/mon-compte")


def test_destination_next_externe_ignoree(client):
    _inscrire(client)

    reponse = _connecter(client, adresse="/compte/connexion?next=https://pirate.example")

    assert "pirate.example" not in reponse.headers["Location"]
    assert reponse.headers["Location"].endswith("/analyse/")


# --- Pages protégées, déconnexion, navbar ----------------------------------------------

def test_page_protegee_renvoie_vers_la_connexion_sans_etre_connecte(client):
    reponse = client.get("/compte/mon-compte")

    assert reponse.status_code == 302
    assert "/compte/connexion" in reponse.headers["Location"]
    assert "next=" in reponse.headers["Location"]


def test_mon_compte_affiche_l_email_quand_connecte(client):
    _inscrire(client)
    _connecter(client)

    reponse = client.get("/compte/mon-compte")

    assert reponse.status_code == 200
    assert EMAIL in reponse.get_data(as_text=True)


def test_deconnexion_ferme_la_session_et_oublie_l_id_session(client):
    _inscrire(client)
    _connecter(client)
    with client.session_transaction() as session:
        session["id_session"] = "sess_du_compte"

    reponse = client.post("/compte/deconnexion")

    assert reponse.status_code == 302
    assert not _est_connecte(client)
    with client.session_transaction() as session:
        assert "id_session" not in session
    assert client.get("/compte/mon-compte").status_code == 302


def test_deconnexion_refuse_les_requetes_get(client):
    _inscrire(client)
    _connecter(client)

    assert client.get("/compte/deconnexion").status_code == 405
    assert _est_connecte(client)


def test_la_navbar_change_selon_l_etat_de_connexion(client):
    visiteur = client.get("/compte/connexion").get_data(as_text=True)
    assert "Se connecter" in visiteur and "Déconnexion" not in visiteur

    _inscrire(client)
    _connecter(client)
    connecte = client.get("/compte/mon-compte").get_data(as_text=True)
    assert "Déconnexion" in connecte and "Mon compte" in connecte
    assert "Se connecter" not in connecte  # ni dans la navbar, ni dans le pied de page


def test_deja_connecte_on_ne_revoit_pas_le_formulaire_de_connexion(client):
    _inscrire(client)
    _connecter(client)

    reponse = client.get("/compte/connexion")

    assert reponse.status_code == 302


# --- CSRF ---------------------------------------------------------------------------------

def test_formulaire_de_connexion_sans_jeton_csrf_refuse():
    app = create_app(ConfigTestAvecCsrf)
    with app.app_context():
        db.create_all()
        reponse = app.test_client().post(
            "/compte/connexion", data={"email": EMAIL, "mot_de_passe": MOT_DE_PASSE}
        )
        db.session.remove()
        db.drop_all()

    assert reponse.status_code == 400