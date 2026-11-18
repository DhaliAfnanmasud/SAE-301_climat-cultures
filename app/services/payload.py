from app.services.openmeteo_client import recuperer_climat, transformer_reponse
from app.services.references import lire_commune, lire_horizon, lire_modele


def _en_entier(valeur, nom):
    """Convertit une valeur reçue en entier. 
    Lève ValueError avec un message clair si ce n'est pas possible.

    `nom` sert uniquement à dire quel champ est en cause dans le message.
    """
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
    Étapes :
        1.  Convertit les id en entiers
        2.  Vérifie que l'horizon et le modèle existent
        3.  On retrouve la commune avec les coordonées/code INSEE)
        4.  On récupère les séries climatiques via Open-Meteo 
        5.  On renvoie le dictionnaire au format du contrat
    Lève ValueError pour toute entrée invalide (avant tout appel à Open-Meteo) et RuntimeError si l'API est indisponible.
    """
    # 1. Les id arrivent souvent sous forme de texte par L'URL ou le formulaire
    id_commune = _en_entier(id_commune, "id_commune")
    id_culture = _en_entier(id_culture, "id_culture")
    id_temps = _en_entier(id_temps, "id_temps")
    id_modele = _en_entier(id_modele, "id_modele")
    
    # 2. Vérification d'un id_commune, id_temps ou id_modèle existant
    commune = lire_commune(id_commune)
    if commune is None:
        raise ValueError("Commune inconnue.")
    horizon = lire_horizon(id_temps)
    if horizon is None:
        raise ValueError("Horizon temporel inconnu.")
    modele = lire_modele(id_modele)
    if modele is None:
        raise ValueError("Modèle climatique inconnu.")
    
    # 3. Appel de l'API Open-Meteo (le cache évite de rappeler l'API pour une requête identique). 
    # Renvoie des listes parallèles : time[], temperature_2m_min[]...
    daily = recuperer_climat(
        commune["latitude"],
        commune["longitude"],
        modele["code_api"],
        horizon["date_debut"],
        horizon["date_fin"],
    )
    
    # 4. On renvoie les données au format du contrat d'interface pour produire le JSON
    # transformer_reponse convertit les listes parallèles en liste de jours {date, t_min, t_max, t_moy, precip}, avec None pour les valeurs manquantes (jamais 0).
    return {
        "id_commune": id_commune,
        "code_insee": commune["code_insee"],
        "id_culture": id_culture,
        "id_temps": id_temps,
        "id_modele": id_modele,
        "id_session": id_session,
        "id_utilisateur": id_utilisateur,   # None tant qu'il n'y a pas de compte
        "latitude": commune["latitude"],
        "series": transformer_reponse(daily),
    }