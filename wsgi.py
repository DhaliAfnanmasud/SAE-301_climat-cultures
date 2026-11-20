import os
from app import create_app
from app.config import DevConfig, ProdConfig

env = os.environ.get('FLASK_ENV', 'development')

config_class = ProdConfig if env == 'production' else DevConfig

if config_class is ProdConfig:
    manquantes = [nom for nom in ("SECRET_KEY", "DATABASE_URL") if not os.environ.get(nom)]
    if manquantes:
        raise RuntimeError("Variables d'environnement manquantes en production : " + ", ".join(manquantes))

app = create_app(config_class)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8100))
    app.run(host='0.0.0.0', port=port)