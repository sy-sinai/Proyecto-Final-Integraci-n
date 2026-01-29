import json
import time
import pika
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Order
from app.database import DATABASE_URL

RABBITMQ_HOST = "rabbitmq"
EXCHANGE = "orders.exchange"
QUEUE = "order.update.queue"
BINDING_KEYS = ["order.confirmed", "order.rejected"]

# BD
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def connect_with_retry(retries=30, delay=2):
    for i in range(retries):
        try:
            return pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
        except Exception:
            print(f"⏳ RabbitMQ no listo ({i+1}/{retries})")
            time.sleep(delay)
    raise Exception("RabbitMQ no disponible")

def start_consumer():
    print("🚀 Order Listener iniciando...")
    connection = connect_with_retry()
    channel = connection.channel()

    # Asegurar exchange
    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type="topic",
        durable=True
    )

    # Cola para resultados
    channel.queue_declare(queue=QUEUE, durable=True)

    # Bind a eventos finales
    for binding_key in BINDING_KEYS:
        channel.queue_bind(
            exchange=EXCHANGE,
            queue=QUEUE,
            routing_key=binding_key
        )

    print(f"📥 Order Listener escuchando {BINDING_KEYS}...")

    def on_message(ch, method, properties, body):
        event = json.loads(body.decode())
        order_id = event.get("order_id")
        status = event.get("status")
        event_type = event.get("event_type")

        print(f"📨 Evento recibido: {event_type} → order_id={order_id}, status={status}")

        # Actualizar BD
        db = SessionLocal()
        try:
            order = db.query(Order).filter(Order.id == order_id).first()
            if order:
                order.status = status
                db.commit()
                print(f"✅ Orden {order_id} actualizada a {status}")
            else:
                print(f"⚠️ Orden {order_id} no encontrada")
        except Exception as e:
            print(f"❌ Error actualizando orden: {e}")
            db.rollback()
        finally:
            db.close()

        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=QUEUE, on_message_callback=on_message)
    channel.start_consuming()
