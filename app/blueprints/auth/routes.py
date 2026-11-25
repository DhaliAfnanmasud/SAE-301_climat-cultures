from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.blueprints.auth import auth_bp
from app.blueprints.auth.validation import est_destination_sure, valider_inscription
from app.extensions import db
from app.models import Utilisateur

# Même message d'ereur pour un e-mail inconnu ou un mauvais mot de passe. On ne révèle pas quelles adresses ont un compte.
MESSAGE_CONNEXION_ECHEC = "E-mail ou mot de passe incorrect."
MESSAGE_EMAIL_INDISPONIBLE = "Impossible de créer un compte avec cette adresse e-mail."

# Hash d'un mot de passe bidon, vérifié quand l'e-mail est inconnu
# La réponse prend le même temps que pour un vrai compte
HASH_FACTICE = generate_password_hash("mot-de-passe-factice")


@auth_bp.route("/inscription", methods=["GET", "POST"])
def inscription():
    if current_user.is_authenticated:
        return redirect(url_for("analyse.tableau_de_bord"))

    email = ""
    if request.method == "POST":
        email = Utilisateur.normaliser_email(request.form.get("email"))
        mot_de_passe = request.form.get("mot_de_passe", "")
        consentement = request.form.get("consentement") == "on"

        erreurs = valider_inscription(email, mot_de_passe, consentement)

        if not erreurs:
            deja_pris = db.session.execute(
                db.select(Utilisateur.id_utilisateur).filter_by(email=email)
            ).first()
            if deja_pris:
                erreurs.append(MESSAGE_EMAIL_INDISPONIBLE)

            utilisateur = Utilisateur(email=email)
            utilisateur.definir_mot_de_passe(mot_de_passe)
            utilisateur.donner_consentement()
            db.session.add(utilisateur)
            try:
                db.session.commit()
            except IntegrityError:
                # Deux inscriptions simultanées avec le même e-mail : la BDD refuse la seconde.
                db.session.rollback()
                erreurs.append(MESSAGE_EMAIL_INDISPONIBLE)
            else:
                flash("Votre compte a été créé. Vous pouvez maintenant vous connecter.", "success")
                return redirect(url_for("auth.connexion"))

        for erreur in erreurs:
            flash(erreur, "danger")

    # Le mot de passe n'est jamais renvoyé dans la page mais l'e-mail oui, pour éviter de le retaper.
    return render_template("auth/inscription.html", email=email)


@auth_bp.route("/connexion", methods=["GET", "POST"])
def connexion():
    if current_user.is_authenticated:
        return redirect(url_for("analyse.tableau_de_bord"))

    if request.method == "POST":
        email = Utilisateur.normaliser_email(request.form.get("email"))
        mot_de_passe = request.form.get("mot_de_passe", "")
        se_souvenir = request.form.get("souvenir") == "on"

        utilisateur = db.session.execute(
            db.select(Utilisateur).filter_by(email=email)
        ).scalar_one_or_none()

        if utilisateur is not None:
            valide = utilisateur.verifier_mot_de_passe(mot_de_passe)
        else:
            check_password_hash(HASH_FACTICE, mot_de_passe)  # voir HASH_FACTICE
            valide = False

        if valide:
            # On repart d'une session vide : l'ancien id_session anonyme est abandonné, un nouveau sera créé.
            session.clear()
            login_user(utilisateur, remember=se_souvenir)
            flash("Vous êtes connecté.", "success")

            cible = request.args.get("next")
            if est_destination_sure(cible):
                return redirect(cible)
            return redirect(url_for("analyse.tableau_de_bord"))

        flash(MESSAGE_CONNEXION_ECHEC, "danger")

    return render_template("auth/connexion.html")


@auth_bp.route("/deconnexion", methods=["POST"])
@login_required
def deconnexion():
    # POST uniquement (avec jeton CSRF) : une simple image ou un lien piégé ne peut pas déconnecter quelqu'un.
    logout_user()
    session.clear()  # le prochain visiteur de ce navigateur aura un nouvel id_session
    flash("Vous êtes déconnecté.", "success")
    return redirect(url_for("main.home"))


@auth_bp.route("/mon-compte")
@login_required
def mon_compte():
    return render_template("auth/mon_compte.html")