import uuid

from flask import session

# Nom de la clé sous laquelle l'identifiant est rangé dans la session Flask
# La session est stockée côté navigateur, dans un cookie signé avec SECRET_KEY.
CLE_SESSION = "id_session"


def obtenir_id_session():
    """Renvoie l'identifiant anonyme du visiteur créé lors de sa première visite.

    L'identifiant est conservé dans la session Flask via un cookie signé et sert à
    rattacher les résultats à un visiteur sans compte (contrat : `id_session`).
    """
    if CLE_SESSION not in session:
        session[CLE_SESSION] = "sess_" + uuid.uuid4().hex
    # Pour les visites suivantes, on renvoie toujours le même identifiant.
    return session[CLE_SESSION]