import hashlib
import json

from sqlalchemy import String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

URL_CACHE = "sqlite:///cache_dev.db"

moteur = create_engine(URL_CACHE)


class Base(DeclarativeBase):
    pass


class CacheApi(Base):
    __tablename__ = "cache_api"

    cle: Mapped[str] = mapped_column(String(32), primary_key=True)
    reponse: Mapped[str] = mapped_column(Text)

Base.metadata.create_all(moteur)

def generer_cle_cache(parametres):
    texte = json.dumps(parametres, sort_keys=True)
    return hashlib.md5(texte.encode("utf-8")).hexdigest()



def lire_cache(cle):
    with Session(moteur) as session:
        ligne = session.get(CacheApi, cle)

        if ligne is None:
            return None

        return json.loads(ligne.reponse)


def ecrire_cache(cle, daily):
    with Session(moteur) as session:
        ligne = CacheApi(cle=cle, reponse=json.dumps(daily))
        session.merge(ligne)
        session.commit()