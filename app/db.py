from sqlalchemy import MetaData
from databases import Database
from sqlalchemy import create_engine

DATABASE_URL = "postgresql://kevin:kevin09@localhost/jwt"

# Async database connection
database = Database(DATABASE_URL)
metadata = MetaData(schema='my_schema')
engine = create_engine(DATABASE_URL)
metadata.create_all(engine)