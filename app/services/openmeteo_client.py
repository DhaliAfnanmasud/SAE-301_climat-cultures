import time
import requests
from datetime import date
import csv
from pathlib import Path
from requests.exceptions import Timeout, RequestException

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

def valider_commune(code_insee):
    with open(
        FICHIER_COMMUNES,
        "r",
        encoding="utf-8-sig"
    ) as fichier:

        lecteur = csv.DictReader(fichier)

        for commune in lecteur:
            if commune["code_insee"] == str(code_insee):
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
                if "daily" not in donnees:
                    print("Données indisponibles pour ce modèle")
                    return None
                return donnees["daily"]
            
            # En cas d'erreur avec le Code 429
            if reponse.status_code == 429:
                erreur_texte = reponse.text
                if "Daily API request limit exceeded" in erreur_texte:
                    print("Erreur 429 : Quota journalier dépassé. Arrêt immédiat.")
                    return None
                else:
                    if tentative == 0:
                        print("Erreur 429 (saturation). Nouvelle tentative dans 2 secondes...")
                        time.sleep(2)
                        tentative += 1
                        continue
                    else:
                        print("Service saturé, réessayez plus tard.")
                        return None
            
            # Gestions des erreurs avec le code serveur 5xx
            elif reponse.status_code >= 500:
                if tentative < max_retries:
                    print(f"Erreur serveur {reponse.status_code}. Tentative ({tentative + 1}/{max_retries + 1})...")
                    tentative += 1
                    time.sleep(1)
                    continue
                else:
                    print("Service indisponible")
                    return None
            else:
                print(f"Erreur client reçue : {reponse.status_code}")
                return None
        
        except(Timeout, RequestException) as e:
            # Si il y a des problèmes réseau ou de timeout
            if tentative < max_retries:
                print(f"Problème réseau ou timeout. Tentative ({tentative + 1}/{max_retries + 1})...")
                tentative += 1
                time.sleep(1)
                continue
            else:
                print("Service indisponible")
                return None
    
    print("Service indisponible")
    return None
                
              

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