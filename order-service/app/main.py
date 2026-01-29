from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Float, DateTime
from .database import SessionLocal, engine, Base
from . import crud, schemas
import jwt
from typing import Optional

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Order Service", description="API de gestión de pedidos con autenticación JWT")

# JWT Config
SECRET_KEY = "tu-clave-secreta-super-segura"
ALGORITHM = "HS256"
security = HTTPBearer(auto_error=False)

# CORS para Demo Portal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_token_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Verifica JWT si está presente (opcional para compatibilidad)."""
    if credentials is None:
        return None  # Permite acceso sin token para demo
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except:
        return None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok", "service": "order-service"}

# Modelo de inventario (mismo que file-ingestor)
from sqlalchemy.orm import declarative_base
InventoryBase = declarative_base()

class InventoryItem(InventoryBase):
    __tablename__ = "inventory_items"
    id = Column(Integer, primary_key=True)
    sku = Column(String, unique=True)
    name = Column(String)
    quantity = Column(Integer)
    price = Column(Float)

@app.get("/inventory")
def get_inventory(db: Session = Depends(get_db)):
    """Obtiene el inventario actual."""
    items = db.query(InventoryItem).all()
    return [{"sku": i.sku, "name": i.name, "quantity": i.quantity, "price": i.price} for i in items]

@app.post("/orders", response_model=schemas.OrderResponse)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db), user: str = Depends(verify_token_optional)):
    """Crear pedido. Acepta JWT opcional en header Authorization: Bearer <token>"""
    return crud.create_order(db, order)

@app.get("/orders", response_model=list[schemas.OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    return crud.get_orders(db)

@app.get("/orders/{order_id}", response_model=schemas.OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = crud.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
