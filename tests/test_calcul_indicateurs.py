"""
Tests du module calcul_indicateurs (pôle DATA).

Copie adaptée au dépôt DEV (tests/) : trois modifications seulement par rapport
à la version du pôle DATA, repérées par « ADAPTATION DEV » :
  1. le module s'importe depuis app/services ;
  2. l'échantillon est aussi cherché dans data/ ;
  3. le test de cohérence SQL est ignoré (skip) si creation_bdd.sql est absent.

Lancement :
    python -m pytest tests/test_calcul_indicateurs.py
"""
import ast
import copy
import glob
import json
import math
import os
import re
import sys
from datetime import date, timedelta

# ADAPTATION DEV (1) : le module est dans app/services (racine du projet dans sys.path)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app.services.calcul_indicateurs import (CULTURES, _et0_hargreaves,  # noqa: E402
                                             _rayonnement_extraterrestre_mm,
                                             calculer_indicateurs, ecrire_fact)

ICI = os.path.dirname(os.path.abspath(__file__))


def _chemin_sample():
    candidats = [os.environ.get("SAMPLE_DATA"),
                 os.path.join(ICI, "sample_data_13.json"),
                 os.path.join(ICI, "..", "data", "sample_data_13.json"),  # ADAPTATION DEV (2)
                 os.path.join(ICI, "..", "DEV", "sample_data_13.json")]
    for c in candidats:
        if c and os.path.exists(c):
            return c
    raise FileNotFoundError("sample_data_13.json introuvable (DATA/ ou ../DEV/)")


def charger():
    with open(_chemin_sample(), encoding="utf-8") as f:
        return json.load(f)


def _serie(debut, jours):
    """jours : liste de (t_min, t_max[, precip]) -> série datée à partir de `debut`."""
    out = []
    for i, j in enumerate(jours):
        out.append({"date": (debut + timedelta(days=i)).isoformat(),
                    "t_min": j[0], "t_max": j[1], "precip": j[2] if len(j) > 2 else 0.0})
    return out


def _payload(series, id_culture=1, **extra):
    p = {"id_commune": 13, "id_culture": id_culture, "id_temps": 2, "id_modele": 1,
         "id_session": "TEST", "series": series}
    p.update(extra)
    return p


def _leve(payload, fragment=""):
    try:
        calculer_indicateurs(payload)
    except ValueError as e:
        assert fragment in str(e), str(e)
        return
    raise AssertionError("ValueError attendue")


# ---------------------------------------------------------------- cas de référence

def test_valeurs_de_reference():
    """Cas 1 du document : gel 20, GDD 3136.9, stress 11, bilan NULL, viable."""
    r = calculer_indicateurs(charger())
    assert (r["jours_gel"], r["gdd"], r["jours_stress_thermique"]) == (20, 3136.9, 11), r
    assert r["bilan_hydrique_mm"] is None and r["verdict"] == "viable", r
    assert r["nb_annees"] == 1 and r["nb_jours_ignores"] == 0 and not r["serie_incomplete"], r


SERIE_SIMPLE = _serie(date(2010, 5, 1), [(2, 12), (-1, 8)]) + [
    {"date": "2010-07-01", "t_min": 18, "t_max": 36, "precip": 0.0},
    {"date": "2010-07-02", "t_min": 15, "t_max": 28, "precip": 0.0},
    {"date": "2010-07-03", "t_min": None, "t_max": None, "precip": None},
]


def test_cas_simple():
    """Cas 2 du document (calculable à la main) : gel 1, GDD 3+1+18+15.5 = 37.5, stress 1."""
    r = calculer_indicateurs(_payload(copy.deepcopy(SERIE_SIMPLE)))
    assert (r["jours_gel"], r["gdd"], r["jours_stress_thermique"]) == (1, 37.5, 1), r
    assert r["nb_jours_ignores"] == 1 and r["serie_incomplete"] is True, r


def test_annee_sans_gel():
    """Cas 3 du document : gel 0, GDD et stress inchangés."""
    p = charger()
    for j in p["series"]:
        j["t_min"] = max(j["t_min"], 1.0)
    r = calculer_indicateurs(p)
    assert (r["jours_gel"], r["gdd"], r["jours_stress_thermique"]) == (0, 3136.9, 11), r


def test_canicule_document():
    """Cas 4 du document : t_max = 38 °C les 40 premiers jours -> gel 20, GDD 3561.6, stress 51."""
    p = charger()
    for j in p["series"][:40]:
        j["t_max"] = 38.0
    r = calculer_indicateurs(p)
    assert (r["jours_gel"], r["gdd"], r["jours_stress_thermique"], r["verdict"]) == (20, 3561.6, 51, "non_viable"), r


def test_canicule_estivale():
    """Vraie canicule : 14 jours consécutifs à 38 °C en juillet. Le stress augmente exactement
    du nombre de jours de la fenêtre qui n'étaient pas déjà en stress ; le gel ne bouge pas."""
    ref = calculer_indicateurs(charger())
    p = charger()
    fenetre = [j for j in p["series"] if "2010-07-15" <= j["date"] <= "2010-07-28"]
    assert len(fenetre) == 14
    deja = sum(1 for j in fenetre if j["t_max"] >= 35)
    for j in fenetre:
        j["t_max"] = 38.0
    r = calculer_indicateurs(p)
    assert r["jours_stress_thermique"] == ref["jours_stress_thermique"] + 14 - deja, r
    assert r["jours_gel"] == ref["jours_gel"] and r["gdd"] >= ref["gdd"], r
    assert r["verdict"] == ("viable" if r["jours_stress_thermique"] <= 15 else "menacee"), r


def test_moyenne_sur_deux_annees():
    """Cas 5 du document."""
    p = charger()
    s2 = copy.deepcopy(p["series"])
    for j in s2:
        j["date"] = "2011" + j["date"][4:]
    p["series"] = p["series"] + s2
    r = calculer_indicateurs(p)
    assert (r["jours_gel"], r["gdd"], r["jours_stress_thermique"], r["nb_annees"]) == (20, 3136.9, 11, 2), r


def test_horizon_onze_annees():
    """Horizon 2040-2050 (11 ans, bornes incluses)."""
    p = charger()
    base = [j for j in p["series"]]
    p["series"] = [dict(j, date=str(y) + j["date"][4:]) for y in range(2040, 2051) for j in base]
    r = calculer_indicateurs(p)
    assert r["nb_annees"] == 11 and r["gdd"] == 3136.9 and r["jours_gel"] == 20, r


def test_erreurs():
    p = charger()
    _leve({**p, "series": []}, "series vide")
    _leve({**p, "id_culture": 99}, "id_culture inconnu : 99")
    for champ in ("id_commune", "id_culture", "id_temps", "id_modele", "series"):
        q = charger()
        del q[champ]
        _leve(q, champ)


# ---------------------------------------------------------------- valeurs manquantes

def test_jour_ignore_si_tmin_absent():
    """Règle du document : t_min OU t_max vide -> le jour est ignoré (aucun indicateur)."""
    s = _serie(date(2010, 7, 1), [(20, 36), (None, 36), (-1, None), (18, 24)])
    r = calculer_indicateurs(_payload(s))
    assert r["jours_stress_thermique"] == 1 and r["jours_gel"] == 0, r   # seul le 1er jour compte
    assert r["nb_jours_ignores"] == 2, r
    assert r["gdd"] == round(((20 + 30) / 2 - 6) + ((18 + 24) / 2 - 6), 1), r   # 19 + 15


def test_valeurs_manquantes_echantillon():
    """Une valeur sur 20 supprimée : aucun indicateur ne peut dépasser la référence."""
    ref = calculer_indicateurs(charger())
    p = charger()
    for i, j in enumerate(p["series"]):
        if i % 20 == 0:
            j["t_min"] = None
        if i % 20 == 10:
            j["precip"] = None
    r = calculer_indicateurs(p)
    assert r["nb_jours_ignores"] == 19, r
    assert r["gdd"] < ref["gdd"] and r["jours_gel"] <= ref["jours_gel"] and r["jours_stress_thermique"] <= ref["jours_stress_thermique"], r


def test_tout_manquant():
    _leve(_payload(_serie(date(2010, 7, 1), [(None, None), (None, 30)])), "aucun jour exploitable")


def test_nan_traite_comme_manquant():
    s = _serie(date(2010, 7, 1), [(float("nan"), 36), (20, 30)])
    r = calculer_indicateurs(_payload(s))
    assert r["nb_jours_ignores"] == 1 and r["jours_stress_thermique"] == 0 and not math.isnan(r["gdd"]), r


def test_tmin_superieure_a_tmax_ignoree():
    r = calculer_indicateurs(_payload(_serie(date(2010, 7, 1), [(25, 15), (20, 30)])))
    assert r["nb_jours_ignores"] == 1 and r["gdd"] == 19.0, r


def test_precip_manquante_avec_latitude():
    """Bilan calculé sur les seuls jours où precip est connue (mêmes jours pour precip et ET0)."""
    p = charger()
    p["latitude"] = 43.6047
    q = copy.deepcopy(p)
    for j in q["series"][100:103]:
        j["precip"] = None
    sans_ces_jours = copy.deepcopy(p)
    sans_ces_jours["series"] = p["series"][:100] + p["series"][103:]
    assert calculer_indicateurs(q)["bilan_hydrique_mm"] == calculer_indicateurs(sans_ces_jours)["bilan_hydrique_mm"]


def test_entrees_invalides():
    s = _serie(date(2010, 7, 1), [(20, 30)])
    _leve(_payload(_serie(date(2010, 7, 1), [("15", 28)])), "t_min")
    _leve(_payload(_serie(date(2010, 7, 1), [(True, 28)])), "t_min")
    _leve(_payload(s + s), "date en double")
    _leve(_payload([{"date": "01/07/2010", "t_min": 1, "t_max": 2}]), "date")
    _leve(_payload(s, latitude=120), "latitude")
    _leve(_payload(s, id_utilisateur="user_test"), "id_utilisateur")


# ---------------------------------------------------------------- bornes et seuils

def test_bornes_gel_et_stress():
    """Gel : strictement < seuil. Stress : >= seuil."""
    assert calculer_indicateurs(_payload(_serie(date(2010, 7, 1), [(0.0, 10)])))["jours_gel"] == 0
    assert calculer_indicateurs(_payload(_serie(date(2010, 7, 1), [(-0.1, 10)])))["jours_gel"] == 1
    assert calculer_indicateurs(_payload(_serie(date(2010, 7, 1), [(20, 35.0)])))["jours_stress_thermique"] == 1
    assert calculer_indicateurs(_payload(_serie(date(2010, 7, 1), [(20, 34.9)])))["jours_stress_thermique"] == 0


def test_plafond_gdd_mais():
    for tx in (30, 40):
        assert calculer_indicateurs(_payload(_serie(date(2010, 7, 1), [(20, tx)])))["gdd"] == 19.0


def test_culture_tournesol():
    """base 6, pas de plafond, gel < -4, stress >= 34."""
    s = _serie(date(2010, 7, 1), [(10, 40), (-5, 5), (-4, 20)])
    r = calculer_indicateurs(_payload(s, id_culture=2))
    assert (r["jours_gel"], r["jours_stress_thermique"]) == (1, 1), r
    assert r["gdd"] == round((10 + 40) / 2 - 6 + 0 + ((6 + 20) / 2 - 6), 1) == 26.0, r


def test_culture_colza():
    """base 0, gel < -15, stress >= 29."""
    s = _serie(date(2010, 7, 1), [(-16, 2), (5, 29)])
    r = calculer_indicateurs(_payload(s, id_culture=3))
    assert (r["jours_gel"], r["jours_stress_thermique"]) == (1, 1), r
    assert r["gdd"] == 1.0 + 17.0, r


def test_culture_pomme_de_terre():
    """base 5, gel < -2, stress >= 28."""
    s = _serie(date(2010, 7, 1), [(10, 28), (-2, 6), (-2.1, 6)])
    r = calculer_indicateurs(_payload(s, id_culture=4))
    assert (r["jours_gel"], r["jours_stress_thermique"]) == (1, 1), r
    assert r["gdd"] == round((10 + 28) / 2 - 5 + ((5 + 6) / 2 - 5) * 2, 1) == 15.0, r


def _serie_verdict(n_stress, n_jours=100, t_min=20, t_max_normal=30):
    return _serie(date(2010, 5, 1), [(t_min, 35 if i < n_stress else t_max_normal) for i in range(n_jours)])


def test_seuils_du_verdict_stress():
    """Maïs, GDD annuel 1900 (> 1600) : viable <= 15 j, menacée <= 30 j, non viable au-delà."""
    for n, attendu in ((15, "viable"), (16, "menacee"), (30, "menacee"), (31, "non_viable")):
        r = calculer_indicateurs(_payload(_serie_verdict(n)))
        assert r["jours_stress_thermique"] == n and r["verdict"] == attendu, (n, r)


def test_seuil_du_verdict_gdd():
    """GDD == GDD de maturité (1600) : pas « non viable » ; 1584 : non viable."""
    assert calculer_indicateurs(_payload(_serie_verdict(0, 100, 20, 24)))["gdd"] == 1600.0
    assert calculer_indicateurs(_payload(_serie_verdict(0, 100, 20, 24)))["verdict"] == "viable"
    r = calculer_indicateurs(_payload(_serie_verdict(0, 99, 20, 24)))
    assert r["gdd"] == 1584.0 and r["verdict"] == "non_viable", r


# ---------------------------------------------------------------- années, saison, bilan

def test_annee_partielle_exclue_de_la_moyenne():
    """1 an complet + 10 jours de l'année suivante : la moyenne ne dilue pas l'année partielle."""
    p = charger()
    p["series"] = p["series"] + [dict(j, date="2011" + j["date"][4:]) for j in p["series"][:10]]
    r = calculer_indicateurs(p)
    assert (r["gdd"], r["jours_gel"], r["nb_annees"], r["nb_annees_incompletes"]) == (3136.9, 20, 1, 1), r
    assert r["serie_incomplete"] is False


def test_annee_bissextile_complete():
    s = _serie(date(2012, 1, 1), [(10, 25)] * 366)
    r = calculer_indicateurs(_payload(s))
    assert r["nb_annees"] == 1 and r["nb_annees_incompletes"] == 0 and not r["serie_incomplete"], r
    assert r["gdd"] == round(366 * (((10 + 25) / 2) - 6), 1), r


def test_saison_restreinte():
    """Avec saison mai-septembre : le gel d'hiver disparaît et le GDD ne compte que la saison."""
    cultures = {1: {**CULTURES[1], "saison": (5, 9)}}
    r = calculer_indicateurs(charger(), cultures=cultures)
    assert (r["jours_gel"], r["gdd"], r["jours_stress_thermique"]) == (0, 2188.8, 11), r
    assert r["nb_annees"] == 1 and not r["serie_incomplete"], r


def test_rayonnement_fao56():
    """Exemple 8 de FAO-56 : 3 septembre (jour 246), 20 °S -> Ra = 32,2 MJ/m²/j = 13,1 mm/j."""
    assert abs(_rayonnement_extraterrestre_mm(-20, 246) - 13.1) < 0.1


def test_et0_hargreaves_proprietes():
    assert _et0_hargreaves(10, 10, 180, 45) == 0.0                 # pas d'amplitude -> 0
    assert _et0_hargreaves(10, 30, 180, 45) > _et0_hargreaves(10, 20, 180, 45) > 0


def test_bilan_hydrique_avec_latitude():
    """Valeur de non-régression (Toulouse 2010 : précip 1000,2 mm, ET0 Hargreaves ≈ 936 mm)."""
    p = charger()
    p["latitude"] = 43.6047
    assert abs(calculer_indicateurs(p)["bilan_hydrique_mm"] - 64.2) < 0.5
    p["latitude"] = 0                                               # latitude 0 valide (équateur)
    assert calculer_indicateurs(p)["bilan_hydrique_mm"] is not None


def test_latitude_absente():
    """Limite 3 du document : sans latitude, bilan NULL, autres indicateurs normaux."""
    r = calculer_indicateurs(_payload(copy.deepcopy(SERIE_SIMPLE)))
    assert r["bilan_hydrique_mm"] is None and r["gdd"] == 37.5, r


# ---------------------------------------------------------------- cohérence avec la base

def test_coherence_dim_culture_sql():
    """Les paramètres de CULTURES doivent être ceux du INSERT INTO Dim_Culture du script SQL."""
    fichiers = glob.glob(os.path.join(ICI, "creation_bdd.sql"))
    if not fichiers:
        # ADAPTATION DEV (3) : ce script appartient au pôle DATA
        try:
            import pytest
        except ImportError:
            return
        pytest.skip("creation_bdd.sql absent du dépôt DEV (test du pôle DATA)")
    assert fichiers, "script de création de la BDD introuvable"
    with open(fichiers[0], encoding="utf-8") as f:
        texte = f.read()
    bloc = texte.split("INSERT INTO Dim_Culture", 1)[1].split(";", 1)[0]
    lignes = [l.strip().rstrip(",") for l in bloc.splitlines() if l.strip().startswith("('")]
    assert len(lignes) == len(CULTURES)
    # (nom, base, plafond, gdd, gel, stade, stress, ...)
    for i, l in enumerate(lignes, start=1):
        v = ast.literal_eval(re.sub(r"\bNULL\b", "None", l))
        c = CULTURES[i]
        assert (v[0], v[1], v[2], v[3], v[4], v[6]) == (
            c["nom"], c["base"], c["plafond"], c["gdd_maturite"], c["seuil_gel"], c["seuil_stress"]), (i, v, c)


# ---------------------------------------------------------------- RGPD

def _payload_minimal(**extra):
    p = {"id_commune": 13, "id_culture": 1, "id_temps": 2, "id_modele": 1,
         "id_session": "TEST_RGPD",
         "series": [{"date": "2010-07-01", "t_min": 18, "t_max": 36, "precip": 0.0},
                    {"date": "2010-07-02", "t_min": 15, "t_max": 28, "precip": 1.0}]}
    p.update(extra)
    return p


def test_rgpd_session_anonyme():
    """Sans id_utilisateur (ou None), le résultat porte id_utilisateur = None."""
    assert calculer_indicateurs(_payload_minimal())["id_utilisateur"] is None
    assert calculer_indicateurs(_payload_minimal(id_utilisateur=None))["id_utilisateur"] is None


def test_rgpd_utilisateur_connecte():
    r = calculer_indicateurs(_payload_minimal(id_utilisateur=999001))
    assert r["id_utilisateur"] == 999001 and r["id_session"] == "TEST_RGPD", r


def test_rgpd_minimisation():
    """Un e-mail ou un nom présent dans le payload n'est jamais recopié dans le résultat."""
    r = calculer_indicateurs(_payload_minimal(id_utilisateur=999001, email="a@b.fr", nom="Dupont", ip="1.2.3.4"))
    assert not {"email", "nom", "ip"} & set(r), r
    assert "a@b.fr" not in json.dumps(r)


class _FauxCurseur:
    def __init__(self, journal): self.journal = journal
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, sql, params): self.journal.append((sql, params))


class _FausseConnexion:
    def __init__(self): self.journal, self.commits = [], 0
    def cursor(self): return _FauxCurseur(self.journal)
    def commit(self): self.commits += 1


def test_rgpd_requete_preparee():
    """ecrire_fact passe toutes les valeurs en paramètres, jamais dans le texte SQL."""
    conn = _FausseConnexion()
    ecrire_fact(conn, calculer_indicateurs(_payload_minimal(id_utilisateur=999001, id_session="x'; DROP TABLE y;--")))
    sql, params = conn.journal[0]
    assert "999001" not in sql and "DROP" not in sql
    assert sql.count("%s") == len(params) == 11
    assert 999001 in params and "x'; DROP TABLE y;--" in params and conn.commits == 1


def test_session_absente_ecrite_vide():
    """id_session est NOT NULL en base : None doit être écrit ''."""
    conn = _FausseConnexion()
    p = _payload_minimal()
    del p["id_session"]
    ecrire_fact(conn, calculer_indicateurs(p))
    assert conn.journal[0][1][5] == ""


if __name__ == "__main__":
    echecs = 0
    for nom, fn in list(globals().items()):
        if nom.startswith("test_"):
            try:
                fn()
                print("OK  ", nom)
            except Exception as e:  # noqa: BLE001
                echecs += 1
                print("ECHEC", nom, "->", repr(e)[:200])
    print(json.dumps(calculer_indicateurs(charger()), ensure_ascii=False, indent=2))
    sys.exit(1 if echecs else 0)