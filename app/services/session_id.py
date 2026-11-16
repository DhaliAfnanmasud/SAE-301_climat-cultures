import uuid

from flask import session

CLE_SESSION = "id_session"


def obtenir_id_session():
    """Renvoie l'identifiant anonyme du visiteur, créé à sa première visite.

    L'identifiant est conservé dans la session Flask via un cookie signé et sert à
    rattacher les résultats à un visiteur sans compte (contrat : `id_session`).
    """
    if CLE_SESSION not in session:
        session[CLE_SESSION] = "sess_" + uuid.uuid4().hex
    return session[CLE_SESSION]