import json
import time
import pika
from app.publisher import publish_payment_result

print("💳 payment consumer cargado")

RABBITMQ_HOST = "rabbitmq"
EXCHANGE = "orders.exchange"
QUEUE = "payment.queue"
BINDING_KEY = "order.validated"

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
    print("🚀 Payment Service iniciando...")
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

    print("📥 Payment Service escuchando order.validated")

    def on_message(ch, method, properties, body):
        event = json.loads(body.decode())
        print("💰 Evento recibido:", event)

        order_id = event["order_id"]

        # Lógica controlada (defendible)
        if order_id % 2 == 0:
            status = "PAID"
        else:
            status = "FAILED"

        publish_payment_result(order_id, status)
        print(f"✅ Pago procesado: {status}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=QUEUE, on_message_callback=on_message)
    channel.start_consuming()
