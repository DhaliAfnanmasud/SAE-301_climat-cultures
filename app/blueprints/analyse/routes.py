from flask import current_app, flash, redirect, render_template, request, url_for

from app.blueprints.analyse import analyse_bp
from app.services.apercu import agreger_par_mois
from app.services.openmeteo_client import valider_commune
from app.services.payload import construire_payload
from app.services.session_id import obtenir_id_session

# --- Valeurs PROVISOIRES ---------------------------
# À remplacer par une lecture de Dim_Culture / Dim_Temps quand DEV 2 aura branché la base.
CULTURES_PROVISOIRES = {
    1: "Maïs grain",
    2: "Tournesol",
    3: "Colza",
    4: "Pomme de terre",
}

HORIZONS_LIBELLES = {
    1: "Référence (2015–2025)",
    2: "Horizon 2050 (2040–2050)",
}

# Modèle climatique par défaut : le choix du modèle viendra en J4.
MODELE_PAR_DEFAUT = 1
# ---------------------------------------------------------------------------


def _culture_connue(valeur):
    """True si `valeur` est l'id d'une culture existante, sinon False."""
    try:
        return int(valeur) in CULTURES_PROVISOIRES
    except (TypeError, ValueError):
        return False


def _page_erreur(message):
    """Affiche la page de résultat avec un message d'erreur clair (HTTP 503)
    à la place d'une page 500 : l'utilisateur peut réessayer."""
    return render_template("analyse/resultat.html", erreur=message), 503


@analyse_bp.route("/resultat")
def resultat():
    """Page de résultat provisoire.

    Exemple : /analyse/resultat?commune=13&culture=1&horizon=2
    Le graphique est l'aperçu des séries climatiques ; l'indicateur de DATA
    arrivera en J3.3.
    """
    commune = request.args.get("commune")
    culture = request.args.get("culture")
    horizon = request.args.get("horizon")

    # Vérification des paramètres obligatoires : sinon on renvoie l'utilisateur à l'accueil.
    if not commune or not culture or not horizon:
        flash("Veuillez choisir une commune, une culture et un horizon.", "warning")
        return redirect(url_for("main.home"))

    # Vérification de la culture
    # Commune, horizon et modèle sont vérifiés dans construire_payload.
    if not _culture_connue(culture):
        flash("Culture inconnue.", "danger")
        return redirect(url_for("main.home"))

    # Construction du payload du contrat (appel Open-Meteo, cache inclus).
    try:
        payload = construire_payload(
            commune, culture, horizon, MODELE_PAR_DEFAUT, obtenir_id_session()
        )
    except ValueError as erreur:
        # Entrée invalide (id inconnu ou modifié) : message clair + retour.
        flash(str(erreur), "danger")
        return redirect(url_for("main.home"))
    
    except RuntimeError as erreur:
        # Open-Meteo indisponible, trop lent ou quota dépassé.
        return _page_erreur(str(erreur))
    
    except Exception:
        # jamais de page 500 pour l'utilisateur.
        current_app.logger.exception("Erreur inattendue sur /analyse/resultat")
        return _page_erreur("Une erreur inattendue est survenue. Veuillez réessayer.")

    # Données de la page pour Chart.js.
    return render_template(
        "analyse/resultat.html",
        erreur=None,
        nom_commune=valider_commune(payload["id_commune"])["nom"],
        nom_culture=CULTURES_PROVISOIRES[payload["id_culture"]],
        libelle_horizon=HORIZONS_LIBELLES.get(payload["id_temps"], "Horizon inconnu"),
        nb_jours=len(payload["series"]),
        donnees=agreger_par_mois(payload["series"]),
    )