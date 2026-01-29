from sqlalchemy.orm import Session
from .models import Order
from .schemas import OrderCreate
from .rabbitmq import publish_order_created
import logging

logger = logging.getLogger(__name__)

def create_order(db: Session, order: OrderCreate):
    """Crea un nuevo pedido y publica evento."""
    try:
        db_order = Order(
            customer_name=order.customer_name,
            product=order.product,
            quantity=order.quantity,
            status="CREATED"
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)

        # Publicar evento
        order_data = {
            "product": db_order.product,
            "quantity": db_order.quantity,
            "customer_name": db_order.customer_name
        }
        correlation_id = publish_order_created(db_order.id, order_data)
        
        # Guardar correlation_id
        db_order.correlation_id = correlation_id
        db.commit()
        db.refresh(db_order)
        
        return db_order

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error creando pedido: {e}")
        raise

def get_orders(db: Session):
    """Obtiene todos los pedidos."""
    return db.query(Order).all()

def get_order_by_id(db: Session, order_id: int):
    """Obtiene un pedido por ID."""
    return db.query(Order).filter(Order.id == order_id).first()
