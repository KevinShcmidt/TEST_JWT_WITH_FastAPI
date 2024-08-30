import sys
import os
from sqlalchemy import create_engine
from models import metadata  # Assurez-vous que 'models' est accessible

# Ajoutez le répertoire parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

DATABASE_URL = "postgresql://kevin:kevin09@localhost/jwt"

# Créez l'engine
engine = create_engine(DATABASE_URL)

# Créez toutes les tables définies dans le metadata
metadata.create_all(engine)
