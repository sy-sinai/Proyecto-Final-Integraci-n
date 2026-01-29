import json
import time
import pika
from app.publisher import publish_payment_result
from app.dlq import setup_dlq

RABBITMQ_HOST = "rabbitmq"
EXCHANGE = "orders.exchange"
QUEUE = "payment.queue"
BINDING_KEY = "order.validated"
MAX_RETRIES = 3

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
    print("🚀 Payment Service iniciando (con DLQ)...")
    connection = connect_with_retry()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type="topic",
        durable=True
    )

    channel.queue_declare(queue=QUEUE, durable=True)

    channel.queue_bind(
        exchange=EXCHANGE,
        queue=QUEUE,
        routing_key=BINDING_KEY
    )
    
    # Configurar DLQ
    setup_dlq(channel, QUEUE)

    print("📥 Payment Service escuchando...")

    def on_message(ch, method, properties, body):
        try:
            event = json.loads(body.decode())
            print(f"💰 Evento recibido: order_id={event['order_id']}")

            order_id = event["order_id"]
            status = "PAID" if order_id % 2 == 0 else "FAILED"

            publish_payment_result(order_id, status)
            print(f"✅ Pago procesado: {status}")

            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            # Reintentos
            retry_count = properties.headers.get("x-retry-count", 0) if properties.headers else 0
            
            if retry_count < MAX_RETRIES:
                print(f"⚠️ Error (reintento {retry_count+1}/{MAX_RETRIES}): {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                time.sleep(2 ** retry_count)
            else:
                print(f"❌ Error final, DLQ: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_consume(queue=QUEUE, on_message_callback=on_message)
    channel.start_consuming()
