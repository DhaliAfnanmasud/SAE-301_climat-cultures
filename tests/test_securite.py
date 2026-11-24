import importlib
import sys

import pytest

from app import create_app
from app.config import DevConfig, ProdConfig


def test_cookies_de_session_sont_httponly_et_samesite():
    # HttpOnly : invisible pour le JavaScript. SameSite=Lax : pas envoyé
    # depuis un formulaire d'un autre site.
    for config in (DevConfig, ProdConfig):
        assert config.SESSION_COOKIE_HTTPONLY is True
        assert config.SESSION_COOKIE_SAMESITE == "Lax"
        assert config.REMEMBER_COOKIE_HTTPONLY is True
        assert config.REMEMBER_COOKIE_SAMESITE == "Lax"


def test_cookie_secure_seulement_en_production():
    # Secure = HTTPS uniquement : impossible en local (http://127.0.0.1).
    assert ProdConfig.SESSION_COOKIE_SECURE is True
    assert ProdConfig.REMEMBER_COOKIE_SECURE is True
    assert DevConfig.SESSION_COOKIE_SECURE is False


def test_la_configuration_est_bien_appliquee_a_lapplication():
    app = create_app()

    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_la_production_n_utilise_jamais_la_cle_par_defaut():
    # La clé par défaut du code ne doit jamais signer les cookies en ligne :
    # soit SECRET_KEY est définie, soit elle est absente (None) et wsgi.py
    # refuse alors de démarrer (test suivant).
    assert ProdConfig.SECRET_KEY != "cle-secrete-dev"


def test_wsgi_refuse_de_demarrer_en_production_sans_variables(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    sys.modules.pop("wsgi", None)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        importlib.import_module("wsgi")

    sys.modules.pop("wsgi", None)