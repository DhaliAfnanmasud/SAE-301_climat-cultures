import time
import requests
from datetime import date
import csv
from pathlib import Path
from requests.exceptions import RequestException
from app.services.cache import ecrire_cache, generer_cle_cache, lire_cache

ENDPOINT = "https://climate-api.open-meteo.com/v1/climate"

VARIABLES = (
    "temperature_2m_min,"
    "temperature_2m_max,"
    "temperature_2m_mean,"
    "precipitation_sum"
)

# Référentiel de communes utilisé temporairement en attendant le branchement de Dim_Commune dans la base de données.
FICHIER_COMMUNES = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "communes-reference.csv"
)

TIMEZONE = "Europe/Paris"
ANNEE_MIN = 1950
ANNEE_MAX = 2050


def valider_dates(date_debut, date_fin):
    try:
        debut = date.fromisoformat(date_debut)
        fin = date.fromisoformat(date_fin)

        if debut.isoformat() != date_debut or fin.isoformat() != date_fin:
            raise ValueError("Format de date invalide.")
    except (TypeError, ValueError):
        raise ValueError("Les dates doivent être au format YYYY-MM-DD.")

    if debut >= fin:
        raise ValueError(
            "La date de début doit être antérieure à la date de fin."
        )

    if debut.year < ANNEE_MIN or fin.year > ANNEE_MAX:
        raise ValueError(
            "La période doit être comprise entre 1950 et 2050."
        )

def valider_commune(id_commune):
    with open(
        FICHIER_COMMUNES,
        "r",
        encoding="utf-8-sig"
    ) as fichier:

        lecteur = csv.DictReader(fichier)

        for commune in lecteur:
            if commune["id_commune"] == str(id_commune):
                return commune

    raise ValueError("Commune inconnue.")


def recuperer_climat(latitude, longitude, modele, date_debut, date_fin):
    # Validation AVANT tout appel à Open-Meteo
    valider_dates(date_debut, date_fin)

    parametres = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": date_debut,
        "end_date": date_fin,
        "models": modele,
        "daily": VARIABLES,
        "timezone": TIMEZONE,
    }

    cle = generer_cle_cache(parametres)
    donnees_cache = lire_cache(cle)

    if donnees_cache is not None:
        return donnees_cache

    max_retries = 2 # 3 tentatives au total (1 tentative initial + 2 réessai)
    tentative = 0

    while tentative <= max_retries:
        try:
            reponse = requests.get(
                ENDPOINT,
                params=parametres,
                timeout=30
            )

            # En cas de succès (Code 200)
            if reponse.status_code == 200:
                donnees = reponse.json()
                daily = donnees.get("daily")

                if not daily or not daily.get("time"):
                    raise RuntimeError("Données indisponibles pour ce modèle.")

                for variable in VARIABLES.split(","):
                    valeurs = daily.get(variable)

                    if not valeurs or all(valeur is None for valeur in valeurs):
                        raise RuntimeError("Données indisponibles pour ce modèle.")

                ecrire_cache(cle, daily)
                return daily
            
            # En cas d'erreur avec le Code 429
            if reponse.status_code == 429:
                if "Daily API request limit exceeded" in reponse.text:
                    raise RuntimeError(
                        "Quota journalier dépassé, réessayez demain."
                    )

                if tentative == 0:
                    print("Erreur 429 (saturation). Nouvelle tentative dans 2 secondes...")
                    time.sleep(2)
                    tentative += 1
                    continue

                raise RuntimeError("Service saturé, réessayez plus tard.")

            # Gestions des erreurs avec le code serveur 5xx
            if reponse.status_code >= 500:
                if tentative < max_retries:
                    print(f"Erreur serveur {reponse.status_code}. Tentative ({tentative + 1}/{max_retries + 1})...")
                    tentative += 1
                    time.sleep(1)
                    continue

                raise RuntimeError("Service indisponible.")

            raise RuntimeError(f"Erreur de requête : {reponse.status_code}.")

        except RequestException:
            # Si il y a des problèmes réseau ou de timeout
            if tentative < max_retries:
                print(f"Problème réseau ou timeout. Tentative ({tentative + 1}/{max_retries + 1})...")
                tentative += 1
                time.sleep(1)
                continue

            raise RuntimeError("Service indisponible.")
                
              

def recuperer_climat_commune(id_commune, modele, date_debut, date_fin):
    commune = valider_commune(id_commune)

    latitude = float(commune["latitude"])
    longitude = float(commune["longitude"])

    return recuperer_climat(
        latitude,
        longitude,
        modele,
        date_debut,
        date_fin
    )