import json
import time
import pika
from datetime import datetime
from app.models import SessionLocal, OrderEvent, Metrics

RABBITMQ_HOST = "rabbitmq"
EXCHANGE = "orders.exchange"
QUEUE = "analytics.queue"
# Escuchar TODOS los eventos de órdenes
BINDING_KEYS = ["order.created", "order.validated", "order.rejected", "order.confirmed"]

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

def update_metric(db, metric_name: str, increment: float = 1):
    """Actualiza o crea una métrica."""
    metric = db.query(Metrics).filter(Metrics.metric_name == metric_name).first()
    if metric:
        metric.metric_value += increment
        metric.updated_at = datetime.utcnow()
    else:
        metric = Metrics(metric_name=metric_name, metric_value=increment)
        db.add(metric)
    db.commit()

def process_event(event: dict):
    """Procesa un evento y actualiza analytics."""
    db = SessionLocal()
    try:
        event_type = event.get("event_type", "Unknown")
        order_id = event.get("order_id")
        status = event.get("status", "")
        correlation_id = event.get("correlation_id", "")
        
        # Guardar evento raw
        order_event = OrderEvent(
            order_id=order_id,
            event_type=event_type,
            status=status,
            correlation_id=correlation_id
        )
        db.add(order_event)
        
        # Actualizar métricas según tipo de evento
        update_metric(db, "total_events")
        
        if event_type == "OrderCreated":
            update_metric(db, "orders_created")
        elif event_type == "InventoryResult":
            if status == "VALIDATED":
                update_metric(db, "inventory_validated")
            else:
                update_metric(db, "inventory_rejected")
        elif event_type == "PaymentResult":
            if status == "PAID":
                update_metric(db, "payments_successful")
                update_metric(db, "orders_completed")
            else:
                update_metric(db, "payments_failed")
        
        db.commit()
        print(f"📊 Analytics: {event_type} order_id={order_id} status={status}")
        
    except Exception as e:
        print(f"❌ Error procesando evento: {e}")
        db.rollback()
    finally:
        db.close()

def start_consumer():
    print("📊 Analytics Service iniciando...")
    connection = connect_with_retry()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type="topic",
        durable=True
    )

    channel.queue_declare(queue=QUEUE, durable=True)

    # Bind a todos los eventos de órdenes
    for binding_key in BINDING_KEYS:
        channel.queue_bind(
            exchange=EXCHANGE,
            queue=QUEUE,
            routing_key=binding_key
        )

    print(f"📥 Analytics escuchando: {BINDING_KEYS}")

    def on_message(ch, method, properties, body):
        try:
            event = json.loads(body.decode())
            process_event(event)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"❌ Error: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_consume(queue=QUEUE, on_message_callback=on_message)
    channel.start_consuming()
