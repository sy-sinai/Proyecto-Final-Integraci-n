import json
import time
import pika
from app.publisher import publish_inventory_result

RABBITMQ_HOST = "rabbitmq"
EXCHANGE = "orders.exchange"
QUEUE = "inventory.queue"
BINDING_KEY = "order.created"

def _connect_with_retry(retries: int = 30, delay: float = 2.0):
    """
    RabbitMQ a veces tarda en estar listo.
    Este método reintenta para evitar que el contenedor se caiga y reinicie.
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
        except Exception as e:
            last_error = e
            print(f"⏳ RabbitMQ no listo (intento {attempt}/{retries}). Reintentando en {delay}s...")
            time.sleep(delay)
    raise last_error

def start_consumer():
    connection = _connect_with_retry()
    channel = connection.channel()

    # 1) asegurar exchange
    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type="topic",
        durable=True
    )

    # 2) crear cola (ESTO es lo que hace que aparezca en RabbitMQ UI)
    channel.queue_declare(queue=QUEUE, durable=True)

    # 3) bind: esta cola recibe eventos order.created
    channel.queue_bind(
        exchange=EXCHANGE,
        queue=QUEUE,
        routing_key=BINDING_KEY
    )

    print("✅ Inventory Service listo.")
    print(f"📥 Escuchando {EXCHANGE} con routing_key='{BINDING_KEY}' en cola '{QUEUE}'...")

    def on_message(ch, method, properties, body):
        try:
            event = json.loads(body.decode("utf-8"))
            print("📩 Evento recibido:", event)

            qty = int(event.get("quantity", 0))
            order_id = int(event.get("order_id"))

            # Lógica mínima real (puedes reemplazarla luego por BD/stock real)
            status = "VALIDATED" if qty <= 10 else "REJECTED"

            publish_inventory_result(order_id=order_id, status=status)

            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(f"✅ Procesado order_id={order_id} → {status}")

        except Exception as e:
            print("❌ Error procesando mensaje:", e)
            # Rechazamos sin requeue para no hacer loop infinito
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE, on_message_callback=on_message)

    channel.start_consuming()
