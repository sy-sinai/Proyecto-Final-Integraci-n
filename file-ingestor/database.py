from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

DATABASE_URL = "postgresql://admin:1234567@postgres:5432/integracion_bd"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Crear tablas
Base.metadata.create_all(bind=engine)
