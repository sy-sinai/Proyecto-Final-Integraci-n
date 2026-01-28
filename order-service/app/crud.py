from sqlalchemy.orm import Session
from .models import Order
from .schemas import OrderCreate
from .rabbitmq import publish_order_created


def create_order(db: Session, order: OrderCreate):
    # 1. Guardar pedido en la BD
    db_order = Order(
        customer_name=order.customer_name,
        product=order.product,
        quantity=order.quantity,
        status="CREATED"
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # 2. Crear evento
    event = {
        "event_type": "OrderCreated",
        "order_id": db_order.id,
        "product": db_order.product,
        "quantity": db_order.quantity,
        "customer_name": db_order.customer_name
    }

    # 3. Publicar evento
    publish_order_created(event)

    return db_order


def get_orders(db: Session):
    return db.query(Order).all()

def get_order_by_id(db: Session, order_id: int):
    return db.query(Order).filter(Order.id == order_id).first()
