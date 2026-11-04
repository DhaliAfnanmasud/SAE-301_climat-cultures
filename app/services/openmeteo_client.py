import requests
from datetime import date
import csv
from pathlib import Path

ENDPOINT = "https://climate-api.open-meteo.com/v1/climate"

VARIABLES = (
    "temperature_2m_min,"
    "temperature_2m_max,"
    "temperature_2m_mean,"
    "precipitation_sum"
)

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

    reponse = requests.get(
        ENDPOINT,
        params=parametres,
        timeout=30
    )

    return reponse.json()["daily"]


def valider_commune(code_insee):
    with open(FICHIER_COMMUNES, "r", encoding="utf-8") as fichier:
        lecteur = csv.DictReader(fichier, delimiter=";")

        for commune in lecteur:
            if commune["code_insee"] == str(code_insee):
                return commune

    raise ValueError("Commune inconnue.")


def recuperer_climat_commune(code_insee, modele, date_debut, date_fin):
    commune = valider_commune(code_insee)

    latitude = float(commune["latitude"])
    longitude = float(commune["longitude"])

    return recuperer_climat(
        latitude,
        longitude,
        modele,
        date_debut,
        date_fin
    )