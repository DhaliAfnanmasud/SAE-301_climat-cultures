import pytest

from app.blueprints.auth.validation import est_destination_sure, valider_inscription

EMAIL = "alice@exemple.fr"
MOT_DE_PASSE = "Motdepasse123"


def test_inscription_valide_sans_erreur():
    assert valider_inscription(EMAIL, MOT_DE_PASSE, True) == []


@pytest.mark.parametrize(
    "email",
    ["", "sans-arobase.fr", "a@b", "a b@exemple.fr", "@exemple.fr", "a@@exemple.fr", "a" * 150 + "@exemple.fr"],
)
def test_email_invalide_refuse(email):
    assert valider_inscription(email, MOT_DE_PASSE, True) != []


@pytest.mark.parametrize("mot_de_passe", ["", "1234567", "x" * 129])
def test_mot_de_passe_hors_limites_refuse(mot_de_passe):
    assert valider_inscription(EMAIL, mot_de_passe, True) != []


def test_mot_de_passe_aux_limites_accepte():
    assert valider_inscription(EMAIL, "x" * 8, True) == []
    assert valider_inscription(EMAIL, "x" * 128, True) == []


def test_consentement_obligatoire():
    erreurs = valider_inscription(EMAIL, MOT_DE_PASSE, False)

    assert len(erreurs) == 1
    assert "accepter" in erreurs[0]


def test_toutes_les_erreurs_sont_remontees_ensemble():
    assert len(valider_inscription("", "court", False)) == 3


@pytest.mark.parametrize("cible", ["/compte/mon-compte", "/analyse/", "/analyse/resultat?commune=13&culture=1&horizon=2"])
def test_destinations_internes_acceptees(cible):
    assert est_destination_sure(cible) is True


@pytest.mark.parametrize(
    "cible",
    [None, "", "mon-compte", "https://pirate.example", "http://pirate.example/x", "//pirate.example",
     "/\\pirate.example", "javascript:alert(1)"],
)
def test_destinations_externes_ou_douteuses_refusees(cible):
    assert est_destination_sure(cible) is False