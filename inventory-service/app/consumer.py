import json
import time
import pika
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from app.publisher import publish_inventory_result
from app.dlq import setup_dlq

RABBITMQ_HOST = "rabbitmq"
EXCHANGE = "orders.exchange"
QUEUE = "inventory.queue"
BINDING_KEY = "order.created"
MAX_RETRIES = 3

# Conexión a BD para verificar stock
DATABASE_URL = "postgresql://admin:1234567@postgres:5432/integracion_bd"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Modelo para Idempotency (mensajes ya procesados)
class ProcessedMessage(Base):
    """Tabla para Idempotent Consumer - evita procesar duplicados."""
    __tablename__ = "processed_messages"
    id = Column(Integer, primary_key=True)
    message_id = Column(String, unique=True, index=True)  # correlation_id o order_id
    service = Column(String, index=True)
    processed_at = Column(DateTime, default=datetime.utcnow)

# Modelo Inventory
class InventoryItem(Base):
    __tablename__ = "inventory_items"
    id = Column(Integer, primary_key=True)
    sku = Column(String, unique=True)
    name = Column(String)
    quantity = Column(Integer)
    price = Column(Float)

# Crear tablas
Base.metadata.create_all(bind=engine)

def is_already_processed(order_id: int) -> bool:
    """Verifica si el mensaje ya fue procesado (Idempotent Consumer)."""
    db = SessionLocal()
    try:
        msg_id = f"inventory-{order_id}"
        exists = db.query(ProcessedMessage).filter(
            ProcessedMessage.message_id == msg_id
        ).first()
        return exists is not None
    finally:
        db.close()

def mark_as_processed(order_id: int):
    """Marca el mensaje como procesado."""
    db = SessionLocal()
    try:
        msg = ProcessedMessage(
            message_id=f"inventory-{order_id}",
            service="inventory-service"
        )
        db.add(msg)
        db.commit()
    except Exception:
        db.rollback()  # Ya existe, ignorar
    finally:
        db.close()

def _connect_with_retry(retries: int = 30, delay: float = 2.0):
    """Conecta a RabbitMQ con reintentos."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
        except Exception as e:
            last_error = e
            print(f"⏳ RabbitMQ no listo ({attempt}/{retries})")
            time.sleep(delay)
    raise last_error

def check_and_reserve_stock(product_sku: str, quantity: int) -> bool:
    """Verifica stock y lo reserva (resta) si hay suficiente."""
    db = SessionLocal()
    try:
        item = db.query(InventoryItem).filter(InventoryItem.sku == product_sku).first()
        
        if not item:
            print(f"❌ Producto {product_sku} no existe en inventario")
            return False
        
        if item.quantity >= quantity:
            # Hay stock suficiente - RESERVAR (restar)
            item.quantity -= quantity
            db.commit()
            print(f"✅ Stock reservado: {product_sku} -{quantity} → Quedan: {item.quantity}")
            return True
        else:
            print(f"❌ Stock insuficiente: {product_sku} tiene {item.quantity}, se pidieron {quantity}")
            return False
    except Exception as e:
        print(f"❌ Error verificando stock: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def start_consumer():
    connection = _connect_with_retry()
    channel = connection.channel()

    # Exchange principal
    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type="topic",
        durable=True
    )

    # Crear queue con DLQ
    channel.queue_declare(queue=QUEUE, durable=True)
    channel.queue_bind(
        exchange=EXCHANGE,
        queue=QUEUE,
        routing_key=BINDING_KEY
    )
    
    # Configurar DLQ
    setup_dlq(channel, QUEUE)

    print("✅ Inventory Service listo (con DLQ)")
    print(f"📥 Escuchando {QUEUE}...")

    def on_message(ch, method, properties, body):
        try:
            event = json.loads(body.decode("utf-8"))
            order_id = int(event.get("order_id"))
            product = event.get("product", "")
            quantity = int(event.get("quantity", 0))
            
            print(f"📩 Evento recibido: order_id={order_id}, producto={product}, qty={quantity}")

            # IDEMPOTENT CONSUMER: Verificar si ya se procesó
            if is_already_processed(order_id):
                print(f"⚠️ IDEMPOTENTE: order_id={order_id} ya fue procesado, ignorando duplicado")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # Verificar stock REAL en BD y reservar
            has_stock = check_and_reserve_stock(product, quantity)
            status = "VALIDATED" if has_stock else "REJECTED"
            
            publish_inventory_result(order_id=order_id, status=status)
            
            # Marcar como procesado
            mark_as_processed(order_id)

            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(f"✅ Procesado order_id={order_id} → {status}")

        except Exception as e:
            # Reintentos con backoff
            retry_count = properties.headers.get("x-retry-count", 0) if properties.headers else 0
            
            if retry_count < MAX_RETRIES:
                print(f"⚠️ Error (reintento {retry_count+1}/{MAX_RETRIES}): {e}")
                # Requeue con delay
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                time.sleep(2 ** retry_count)  # Backoff exponencial: 1s, 2s, 4s
            else:
                print(f"❌ Error final, enviando a DLQ: {e}")
                # Enviar a DLQ
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE, on_message_callback=on_message)
    channel.start_consuming()
