import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "cle-secrete-dev")
    SQLALCHEMY_TRACK_MODIFICATIONS = False


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
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")