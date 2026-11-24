import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "cle-secrete-dev")
    SQLALCHEMY_TRACK_MODIFICATIONS = False    
    
    # Cookies de session  :
    # - Secure : réservé à la production (HTTPS), voir ProdConfig.
    SESSION_COOKIE_HTTPONLY = True  # HttpOnly : le cookie est invisible pour le JavaScript de la page ;
    SESSION_COOKIE_SAMESITE = "Lax" # SameSite=Lax : il n'est pas envoyé lors d'un envoi de formulaire venant d'un autre site(défense en plus du jeton CSRF) ;
    SESSION_COOKIE_SECURE = False   # Secure : réservé à la production HTTPS.
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = False


class DevConfig(Config):
    DEBUG = True

    DB_HOST = os.environ.get("DB_HOST")
    DB_NAME = os.environ.get("DB_NAME")
    DB_USER = os.environ.get("DB_USER")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:"
        f"{quote_plus(DB_PASSWORD or '')}@"
        f"{DB_HOST}/{DB_NAME}?charset=utf8mb4"
    )


class ProdConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")