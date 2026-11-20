"""
Module de calcul des indicateurs — SAÉ 3.01 « Climat & Cultures » (pôle DATA)

Entrée  : payload JSON du CONTRAT_INTERFACE.md (section 2), sous forme de dict.
Sortie  : dict prêt à être sérialisé en JSON / inséré dans Fact_Indicateur (section 3 du contrat).

Formules (validées sur sample_data_13.json : gel 20, GDD 3136.9, stress 11) :
  - jours_gel              : nb de jours avec t_min  <  seuil_gel
  - jours_stress_thermique : nb de jours avec t_max  >= seuil_stress
  - gdd                    : somme de ((max(t_min, base) + min(t_max, plafond)) / 2) - base,
                             jour par jour, bornée à 0 (méthode des degrés-jours "plafonnés")
  - bilan_hydrique_mm      : somme(precip) - somme(ET0 Hargreaves), si la latitude est connue

Valeurs manquantes (règle unique, identique au document d'explication) :
  un jour dont t_min ou t_max est absent (null / NaN), ou incohérent (t_min > t_max),
  est IGNORÉ pour tous les indicateurs. Pour le bilan hydrique, un jour sans precip est
  aussi écarté (précipitations et ET0 sont toujours cumulées sur les mêmes jours).
  Le nombre de jours ignorés est renvoyé (nb_jours_ignores).

Séries pluriannuelles (horizon 2040-2050) : on calcule chaque année puis on fait la
MOYENNE PAR AN. Une année « incomplète » (< 90 % des jours attendus) est exclue de la
moyenne, sauf si aucune année n'est complète (série courte de test) : on calcule alors
sur ce qu'on a et on renvoie serie_incomplete = True.

LIMITE ASSUMÉE (à arbitrer par l'équipe) : par défaut les indicateurs portent sur
l'ANNÉE ENTIÈRE. Le gel d'hiver et le GDD hors saison ne sont pas agronomiquement
pertinents pour une culture de printemps. Le paramètre "saison" = (mois_debut, mois_fin)
de chaque culture permet de restreindre le calcul ; il vaut None par défaut pour ne pas
changer les valeurs de référence des documents.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta

# Parametres des cultures : doivent rester identiques a Dim_Culture
# (verifie par test_coherence_dim_culture_sql). A terme : les lire en base.
# "saison" : (mois_debut, mois_fin) inclus, None = annee entiere.

CULTURES = {
    1: {"nom": "Maïs grain",      "base": 6, "plafond": 30,   "seuil_gel": 0,   "seuil_stress": 35, "gdd_maturite": 1600, "saison": None},
    2: {"nom": "Tournesol",       "base": 6, "plafond": None, "seuil_gel": -4,  "seuil_stress": 34, "gdd_maturite": 1500, "saison": None},
    3: {"nom": "Colza",           "base": 0, "plafond": None, "seuil_gel": -15, "seuil_stress": 29, "gdd_maturite": 2330, "saison": None},
    4: {"nom": "Pomme de terre",  "base": 5, "plafond": None, "seuil_gel": -2,  "seuil_stress": 28, "gdd_maturite": 1050, "saison": None},
}

# Verdict — RÈGLE PROVISOIRE (à remplacer par la règle validée de l'équipe).
# ids = ordre d'insertion de Dim_Verdict : 1 = viable, 2 = menacee, 3 = non_viable.
VERDICTS = {1: "viable", 2: "menacee", 3: "non_viable"}
SEUIL_STRESS_VIABLE = 15    # jours/an de stress thermique : <= 15 -> viable
SEUIL_STRESS_MENACEE = 30   # <= 30 -> menacée, au-delà -> non viable

AGREGATION = "moyenne"      # "moyenne" (par an) ou "somme" sur toute la série
COUVERTURE_MIN = 0.9        # part minimale des jours attendus pour qu'une année soit « complète »

CHAMPS_OBLIGATOIRES = ("id_commune", "id_culture", "id_temps", "id_modele", "series")


# Validation / lecture des entrées

def _nombre(valeur, champ):
    """Renvoie un float, ou None si la valeur est absente (None / NaN). ValueError si ce n'est pas un nombre."""
    if valeur is None:
        return None
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
        raise ValueError(f"{champ} doit être un nombre ou null, reçu : {valeur!r}")
    if math.isnan(valeur):
        return None
    if math.isinf(valeur):
        raise ValueError(f"{champ} infini : {valeur!r}")
    return float(valeur)


def _lire_serie(series):
    """Transforme la série JSON en liste triée de (date, t_min, t_max, precip)."""
    jours, vues = [], set()
    for i, j in enumerate(series):
        try:
            d = date.fromisoformat(j["date"])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"series[{i}] : date absente ou invalide (format YYYY-MM-DD attendu)")
        if d in vues:
            raise ValueError(f"series[{i}] : date en double ({d.isoformat()})")
        vues.add(d)
        jours.append((d,
                      _nombre(j.get("t_min"), f"series[{i}].t_min"),
                      _nombre(j.get("t_max"), f"series[{i}].t_max"),
                      _nombre(j.get("precip"), f"series[{i}].precip")))
    jours.sort(key=lambda x: x[0])
    return jours


def _dans_saison(d, saison):
    if saison is None:
        return True
    debut, fin = saison
    return debut <= d.month <= fin if debut <= fin else (d.month >= debut or d.month <= fin)


def _jours_attendus(annee, saison):
    """Nombre de jours que doit contenir une année complète (dans la saison si elle est définie)."""
    d, n = date(annee, 1, 1), 0
    while d.year == annee:
        n += _dans_saison(d, saison)
        d += timedelta(days=1)
    return n


# Indicateurs journaliers

def _gdd_jour(t_min, t_max, base, plafond):
    """Degrés-jours d'une journée (méthode plafonnée, validée sur l'exemple)."""
    tn = max(t_min, base)
    tx = t_max if plafond is None else min(t_max, plafond)
    tx = max(tx, base)
    return max((tn + tx) / 2 - base, 0.0)


def _rayonnement_extraterrestre_mm(lat_deg: float, jour_annee: int) -> float:
    """Ra en mm/jour équivalent évaporation (FAO-56, éq. 21)."""
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * jour_annee / 365)
    delta = 0.409 * math.sin(2 * math.pi * jour_annee / 365 - 1.39)
    x = max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta)))
    ws = math.acos(x)
    ra_mj = (24 * 60 / math.pi) * 0.0820 * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws)
    )
    return 0.408 * ra_mj


def _et0_hargreaves(t_min, t_max, jour_annee, lat_deg):
    """ET0 Hargreaves-Samani (mm/jour) : 0.0023 * Ra * (Tmoy + 17.8) * sqrt(Tmax - Tmin)."""
    ra = _rayonnement_extraterrestre_mm(lat_deg, jour_annee)
    t_moy = (t_min + t_max) / 2
    return max(0.0023 * ra * (t_moy + 17.8) * math.sqrt(max(t_max - t_min, 0.0)), 0.0)


# Calcul sur une année

def _indicateurs_annee(jours, culture, latitude):
    """jours : liste de (date, t_min, t_max, precip) d'une même année, déjà filtrée sur la saison."""
    gel = stress = ignores = 0
    gdd = precip = et0 = 0.0
    for d, t_min, t_max, p in jours:
        if t_min is None or t_max is None or t_min > t_max:
            ignores += 1
            continue
        if t_min < culture["seuil_gel"]:
            gel += 1
        if t_max >= culture["seuil_stress"]:
            stress += 1
        gdd += _gdd_jour(t_min, t_max, culture["base"], culture["plafond"])
        if latitude is not None and p is not None:
            precip += p
            et0 += _et0_hargreaves(t_min, t_max, d.timetuple().tm_yday, latitude)
    bilan = (precip - et0) if latitude is not None else None
    return {"jours_gel": gel, "gdd": gdd, "jours_stress_thermique": stress,
            "bilan_hydrique_mm": bilan, "ignores": ignores}


def _verdict(gdd, jours_stress, culture):
    if gdd < culture["gdd_maturite"]:
        return 3
    if jours_stress <= SEUIL_STRESS_VIABLE:
        return 1
    if jours_stress <= SEUIL_STRESS_MENACEE:
        return 2
    return 3


# Point d'entrée

def calculer_indicateurs(payload: dict, cultures: dict | None = None) -> dict:
    """Calcule les indicateurs à partir d'un payload du contrat d'interface.

    Lève ValueError (message explicite) si le payload ne respecte pas le contrat.
    `latitude` (°, optionnelle) est nécessaire au bilan hydrique.
    """
    cultures = cultures or CULTURES
    for champ in CHAMPS_OBLIGATOIRES:
        if champ not in payload or payload[champ] is None:
            raise ValueError(f"champ obligatoire manquant : {champ}")

    id_culture = payload["id_culture"]
    if id_culture not in cultures:
        raise ValueError(f"id_culture inconnu : {id_culture}")
    culture = {**{"saison": None}, **cultures[id_culture]}

    id_utilisateur = payload.get("id_utilisateur")
    if id_utilisateur is not None and (isinstance(id_utilisateur, bool) or not isinstance(id_utilisateur, int)):
        raise ValueError(f"id_utilisateur doit être un entier ou null, reçu : {id_utilisateur!r}")

    latitude = _nombre(payload.get("latitude"), "latitude")
    if latitude is not None and not -90 <= latitude <= 90:
        raise ValueError(f"latitude hors de [-90, 90] : {latitude}")

    series = payload["series"]
    if not series:
        raise ValueError("series vide : impossible de calculer les indicateurs")
    jours = [j for j in _lire_serie(series) if _dans_saison(j[0], culture["saison"])]
    if not any(t_min is not None and t_max is not None and t_min <= t_max for _, t_min, t_max, _ in jours):
        raise ValueError("aucun jour exploitable (t_min / t_max absents ou incohérents)")

    par_annee = defaultdict(list)
    for j in jours:
        par_annee[j[0].year].append(j)

    complete = {a: len(js) >= COUVERTURE_MIN * _jours_attendus(a, culture["saison"])
                for a, js in par_annee.items()}
    serie_incomplete = not any(complete.values())
    annees = [a for a in sorted(par_annee) if complete[a] or serie_incomplete]
    resultats = [_indicateurs_annee(par_annee[a], culture, latitude) for a in annees]
    n = len(resultats)
    diviseur = n if AGREGATION == "moyenne" else 1

    def agreger(cle):
        valeurs = [r[cle] for r in resultats]
        if any(v is None for v in valeurs):
            return None
        return sum(valeurs) / diviseur

    jours_gel = round(agreger("jours_gel"), 1)
    jours_stress = round(agreger("jours_stress_thermique"), 1)
    gdd = round(agreger("gdd"), 1)
    bilan = agreger("bilan_hydrique_mm")
    bilan = None if bilan is None else round(bilan, 1)

    id_verdict = _verdict(gdd, jours_stress, culture)
    return {
        "id_commune": payload["id_commune"],
        "id_culture": id_culture,
        "id_temps": payload["id_temps"],
        "id_modele": payload["id_modele"],
        "id_session": payload.get("id_session"),
        "id_utilisateur": id_utilisateur,
        "jours_gel": jours_gel,
        "gdd": gdd,
        "jours_stress_thermique": jours_stress,
        "bilan_hydrique_mm": bilan,
        "id_verdict": id_verdict,
        "verdict": VERDICTS[id_verdict],
        "nb_annees": n,
        "nb_annees_incompletes": len(par_annee) - sum(complete.values()),
        "serie_incomplete": serie_incomplete,
        "nb_jours_ignores": sum(r["ignores"] for r in resultats),
    }


# Écriture dans Fact_Indicateur (connexion DB-API fournie par l'appelant,
# ex. mysql.connector ou PyMySQL — aucun identifiant n'est écrit ici).

SQL_UPSERT = """
INSERT INTO Fact_Indicateur
  (id_commune, id_culture, id_temps, id_modele, id_verdict, id_session,
   id_utilisateur, jours_gel, gdd, jours_stress_thermique, bilan_hydrique_mm, date_calcul)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
ON DUPLICATE KEY UPDATE
  id_verdict = VALUES(id_verdict), jours_gel = VALUES(jours_gel), gdd = VALUES(gdd),
  jours_stress_thermique = VALUES(jours_stress_thermique),
  bilan_hydrique_mm = VALUES(bilan_hydrique_mm), date_calcul = NOW()
"""


def ecrire_fact(conn, resultat: dict) -> None:
    """Insère (ou met à jour) la ligne dans Fact_Indicateur (contrainte uq_fait).

    id_session est NOT NULL DEFAULT '' en base : une session absente (None) est écrite ''.
    """
    r = resultat
    with conn.cursor() as cur:
        cur.execute(SQL_UPSERT, (
            r["id_commune"], r["id_culture"], r["id_temps"], r["id_modele"], r["id_verdict"],
            r["id_session"] or "", r["id_utilisateur"], r["jours_gel"], r["gdd"],
            r["jours_stress_thermique"], r["bilan_hydrique_mm"],
        ))
    conn.commit()
