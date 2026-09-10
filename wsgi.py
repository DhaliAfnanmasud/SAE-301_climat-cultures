import os
from app import create_app
from app.config import DevConfig, ProdConfig

env = os.environ.get('FLASK_ENV', 'development')
config_class = ProdConfig if env == 'production' else DevConfig

app = create_app(config_class)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8100))
    app.run(host='0.0.0.0', port=port)
    
