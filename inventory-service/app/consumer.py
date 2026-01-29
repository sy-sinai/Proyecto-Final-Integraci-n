import json
import time
import pika
from app.publisher import publish_inventory_result
from app.dlq import setup_dlq

RABBITMQ_HOST = "rabbitmq"
EXCHANGE = "orders.exchange"
QUEUE = "inventory.queue"
BINDING_KEY = "order.created"
MAX_RETRIES = 3

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
            print(f"📩 Evento recibido: order_id={event.get('order_id')}")

            qty = int(event.get("quantity", 0))
            order_id = int(event.get("order_id"))

            # Validar
            status = "VALIDATED" if qty <= 10 else "REJECTED"
            publish_inventory_result(order_id=order_id, status=status)

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
