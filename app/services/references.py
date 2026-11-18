"""Lecture des tables de référence pour le DEV 3.

Chaque fonction reçoit un id (entier ou texte venant de l'URL) et renvoie un
dictionnaire simple, ou None si l'id est invalide ou inexistant. Elles
doivent être appelées dans un contexte Flask (requête en cours).

Renvoyer des dictionnaires (et non des objets SQLAlchemy) permet de tester
payload.py et les routes sans base de données : les tests remplacent ces
fonctions par de fausses réponses.
"""
from app.extensions import db
from app.models import DimCommune, DimCulture, DimModele, DimTemps


def _en_entier(valeur):
    """Convertit en entier, ou renvoie None si ce n'est pas possible."""
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return None


def _lire(modele, identifiant):
    """Lit une ligne par clé primaire ; None si l'id est invalide ou absent."""
    identifiant = _en_entier(identifiant)
    if identifiant is None:
        return None
    return db.session.get(modele, identifiant)


def lire_commune(id_commune):
    commune = _lire(DimCommune, id_commune)
    if commune is None:
        return None
    return {
        "id_commune": commune.id_commune,
        "code_insee": commune.code_insee,
        "nom": commune.nom_commune,
        # La base renvoie des Decimal : on convertit en float pour l'API.
        "latitude": float(commune.latitude),
        "longitude": float(commune.longitude),
    }


def lire_culture(id_culture):
    culture = _lire(DimCulture, id_culture)
    if culture is None:
        return None
    return {"id_culture": culture.id_culture, "nom": culture.nom_culture}


def lire_horizon(id_temps):
    """Horizon temporel : les dates sont reconstruites depuis les années
    (annee_debut -> 1er janvier, annee_fin -> 31 décembre)."""
    temps = _lire(DimTemps, id_temps)
    if temps is None:
        return None
    return {
        "id_temps": temps.id_temps,
        "libelle": f"{temps.horizon} ({temps.annee_debut}–{temps.annee_fin})",
        "date_debut": f"{temps.annee_debut}-01-01",
        "date_fin": f"{temps.annee_fin}-12-31",
    }


def lire_modele(id_modele):
    modele = _lire(DimModele, id_modele)
    if modele is None:
        return None
    return {"id_modele": modele.id_modele, "code_api": modele.code_api}