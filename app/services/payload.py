from app.services.openmeteo_client import recuperer_climat, transformer_reponse, valider_commune

# --- Correspondances provisoires en attente de la fonction qui appel la BDD -------------------------------------------

HORIZONS_PROVISOIRES = {
    1: ("2015-01-01", "2025-12-31"),  # plage de réference
    2: ("2040-01-01", "2050-12-31"),  #  prévisions pour 2040-2050
}

MODELES_PROVISOIRES = {
    1: "MRI_AGCM3_2_S",
    2: "CMCC_CM2_VHR4",
}
# ---------------------------------------------------------------------------

def _en_entier(valeur, nom):
    try:
        return int (valeur)
    except (TypeError, ValueError):
        raise ValueError(f"{nom} doit être un entier, reçu : {valeur!r}.")


def construire_payload (
    id_commune,
    id_culture,
    id_temps,
    id_modele,
    id_session,
    id_utilisateur=None,
):
    
    """Assemble le JSON du contrat d'interface DEV -> DATA.
    Lève ValueError pour toute entrée invalide (avant tout appel à Open-Meteo) et RuntimeError si l'API est indisponible.
    """
    id_commune = _en_entier(id_commune, "id_commune")
    id_culture = _en_entier(id_culture, "id_culture")
    id_temps = _en_entier(id_temps, "id_temps")
    id_modele = _en_entier(id_modele, "id_modele")
    
    if id_temps not in HORIZONS_PROVISOIRES:
        raise ValueError("Horizon temporel inconnu.")
    if id_modele not in MODELES_PROVISOIRES:
        raise ValueError("Modèle climatique inconnu.")
    
    commune = valider_commune(id_commune)
    latitude = float(commune["latitude"])
    longitude = float(commune["longitude"])
    date_debut, date_fin = HORIZONS_PROVISOIRES[id_temps]
    
    daily = recuperer_climat(
        latitude,
        longitude,
        MODELES_PROVISOIRES[id_modele],
        date_debut,
        date_fin,
    )
    
    return {
        "id_commune": id_commune,
        "code_insee": commune["code_insee"],
        "id_culture": id_culture,
        "id_temps": id_temps,
        "id_modele": id_modele,
        "id_session": id_session,
        "id_utilisateur": id_utilisateur,
        "latitude": latitude,
        "series": transformer_reponse(daily),
    }