from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

DATABASE_URL = "postgresql://admin:1234567@postgres:5432/integracion_bd"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class OrderEvent(Base):
    """Registro de todos los eventos de órdenes para analytics."""
    __tablename__ = "order_events"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, index=True)
    event_type = Column(String, index=True)  # OrderCreated, InventoryResult, PaymentResult
    status = Column(String)  # CREATED, VALIDATED, REJECTED, PAID, FAILED
    correlation_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Metrics(Base):
    """Métricas agregadas en tiempo real."""
    __tablename__ = "analytics_metrics"
    
    id = Column(Integer, primary_key=True)
    metric_name = Column(String, unique=True, index=True)
    metric_value = Column(Float, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Crear tablas
Base.metadata.create_all(bind=engine)
