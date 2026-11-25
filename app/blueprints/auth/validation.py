import re
from urllib.parse import urlparse

"""Fonctions de validation de l'inscription et de la redirection après connexion.
"""
# définition de la longeur min et max du mot de passe
LONGUEUR_MIN_MOT_DE_PASSE = 8
LONGUEUR_MAX_MOT_DE_PASSE = 128

# Taille de la colonne Utilisateur.email dans la base.
LONGUEUR_MAX_EMAIL = 150

# Format : « quelque chose @ quelque chose . quelque chose », sans espace : suffisant pour détecter une faute de frappe 
_MOTIF_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def valider_inscription(email, mot_de_passe, consentement):
    """Renvoie la liste des messages d'erreur
    Une liste vide signifie que tout est valide).

    `email` doit déjà être normalisé (espaces retirés, minuscules).
    """
    erreurs = []

    if not email:
        erreurs.append("Veuillez saisir votre adresse e-mail.")
    elif len(email) > LONGUEUR_MAX_EMAIL or not _MOTIF_EMAIL.match(email):
        erreurs.append("L'adresse e-mail n'est pas valide.")

    if len(mot_de_passe) < LONGUEUR_MIN_MOT_DE_PASSE:
        erreurs.append(
            f"Le mot de passe doit contenir au moins {LONGUEUR_MIN_MOT_DE_PASSE} caractères."
        )
    elif len(mot_de_passe) > LONGUEUR_MAX_MOT_DE_PASSE:
        erreurs.append(
            f"Le mot de passe ne doit pas dépasser {LONGUEUR_MAX_MOT_DE_PASSE} caractères."
        )

    if not consentement:
        erreurs.append(
            "Vous devez accepter les conditions d'utilisation et la politique "
            "de confidentialité pour créer un compte."
        )

    return erreurs


def est_destination_sure(cible):
    """True seulement pour un chemin interne au site (ex. « /compte/mon-compte »).

    Le paramètre ?next= vient de l'URL, donc de l'extérieur : sans ce contrôle,
    un lien piégé pourrait renvoyer l'utilisateur vers un site malveillant
    juste après sa connexion.
    """
    if not cible or not cible.startswith("/"):
        return False
    # « // » et « /\ » sont lus par les navigateurs comme « http://autre-site ».
    if cible.startswith("//") or "\\" in cible:
        return False
    morceaux = urlparse(cible)
    return not morceaux.scheme and not morceaux.netloc