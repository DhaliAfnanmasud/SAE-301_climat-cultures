import requests

ENDPOINT = "https://climate-api.open-meteo.com/v1/climate"

VARIABLES = "temperature_2m_min,temperature_2m_max,temperature_2m_mean,precipitation_sum"

TIMEZONE = "Europe/Paris"


def recuperer_climat(latitude, longitude, modele, date_debut, date_fin):
    parametres = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": date_debut,
        "end_date": date_fin,
        "models": modele,
        "daily": VARIABLES,
        "timezone": TIMEZONE,
    }

    reponse = requests.get(ENDPOINT, params=parametres, timeout=30)

    return reponse.json()["daily"]