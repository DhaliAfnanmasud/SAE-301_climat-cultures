from flask import current_app, flash, redirect, render_template, request, url_for

from app.blueprints.analyse import analyse_bp
from app.extensions import db
from app.models import DimCommune, DimCulture, DimTemps
from app.services.apercu import agreger_par_mois
from app.services.payload import construire_payload
from app.services.references import lire_commune, lire_culture, lire_horizon
from app.services.session_id import obtenir_id_session

# Modèle climatique par défaut : le choix du modèle viendra en J4.
MODELE_PAR_DEFAUT = 1


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
        return redirect(url_for("analyse.tableau_de_bord"))

    try:
        # La culture est vérifiée ici ; commune, horizon et modèle le sont
        # dans construire_payload. Tout est lu en base (jamais de confiance
        # envers l'URL, qui peut être modifiée).
        culture_ref = lire_culture(culture)
        if culture_ref is None:
            raise ValueError("Culture inconnue.")

        # Construction du payload du contrat (appel Open-Meteo, cache inclus).
        payload = construire_payload(
            commune, culture, horizon, MODELE_PAR_DEFAUT, obtenir_id_session()
        )

        # Noms à afficher dans le rappel du choix.
        nom_commune = lire_commune(payload["id_commune"])["nom"]
        horizon_ref = lire_horizon(payload["id_temps"])
    except ValueError as erreur:
        # Entrée invalide (id inconnu ou modifié) : message clair + retour.
        flash(str(erreur), "danger")
        return redirect(url_for("analyse.tableau_de_bord"))
    except RuntimeError as erreur:
        # Open-Meteo indisponible, trop lent ou quota dépassé.
        return _page_erreur(str(erreur))
    except Exception:
        # Jamais de page 500 pour l'utilisateur (base injoignable, bug...).
        current_app.logger.exception("Erreur inattendue sur /analyse/resultat")
        return _page_erreur("Une erreur inattendue est survenue. Veuillez réessayer.")

    # Données de la page pour Chart.js.
    return render_template(
        "analyse/resultat.html",
        erreur=None,
        nom_commune=nom_commune,
        nom_culture=culture_ref["nom"],
        libelle_horizon=horizon_ref["libelle"],
        nb_jours=len(payload["series"]),
        donnees=agreger_par_mois(payload["series"]),
    )


@analyse_bp.route("/", methods=["GET", "POST"])
def tableau_de_bord():
    communes = DimCommune.query.order_by(DimCommune.nom_commune).all()
    cultures = DimCulture.query.order_by(DimCulture.nom_culture).all()
    horizons = DimTemps.query.order_by(DimTemps.id_temps).all()

    if request.method == "POST":
        commune = request.form.get("commune")
        culture = request.form.get("culture")
        horizon = request.form.get("horizon")

        # Vérifie que les trois champs sont présents
        if not commune or not culture or not horizon:
            flash("Tous les champs sont obligatoires.", "danger")
            return redirect(url_for("analyse.tableau_de_bord"))

        # Vérifie que les valeurs reçues sont bien des entiers
        try:
            id_commune = int(commune)
            id_culture = int(culture)
            id_temps = int(horizon)
        except ValueError:
            flash("Les paramètres envoyés sont invalides.", "danger")
            return redirect(url_for("analyse.tableau_de_bord"))

        # Vérifie que les identifiants existent réellement dans la BDD
        commune_bdd = db.session.get(DimCommune, id_commune)
        culture_bdd = db.session.get(DimCulture, id_culture)
        temps_bdd = db.session.get(DimTemps, id_temps)

        if commune_bdd is None:
            flash("Commune inconnue.", "danger")
            return redirect(url_for("analyse.tableau_de_bord"))

        if culture_bdd is None:
            flash("Culture inconnue.", "danger")
            return redirect(url_for("analyse.tableau_de_bord"))

        if temps_bdd is None:
            flash("Horizon temporel inconnu.", "danger")
            return redirect(url_for("analyse.tableau_de_bord"))

        # Tout est valide : on passe les ids à DEV 3
        return redirect(
            url_for(
                "analyse.resultat",
                commune=id_commune,
                culture=id_culture,
                horizon=id_temps,
            )
        )

    return render_template(
        "analyse/tableau_de_bord.html",
        communes=communes,
        cultures=cultures,
        horizons=horizons,
    )