import json
import time
import pika

RABBITMQ_HOST = "rabbitmq"
EXCHANGE = "orders.exchange"
QUEUE = "notification.queue"
BINDING_KEYS = ["order.confirmed", "order.rejected"]

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
    print("🚀 Notification Service iniciando...")
    connection = connect_with_retry()
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type="topic",
        durable=True
    )

    channel.queue_declare(queue=QUEUE, durable=True)

    for binding_key in BINDING_KEYS:
        channel.queue_bind(
            exchange=EXCHANGE,
            queue=QUEUE,
            routing_key=binding_key
        )

    print("📧 Notification Service escuchando órdenes...")

    def on_message(ch, method, properties, body):
        event = json.loads(body.decode())
        print(f"📧 Notificación: {event}")

        order_id = event.get("order_id")
        status = event.get("status", "UNKNOWN")
        
        if status == "PAID":
            print(f"✅ Orden {order_id} CONFIRMADA - Cliente notificado")
        else:
            print(f"❌ Orden {order_id} RECHAZADA - Cliente notificado")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=QUEUE, on_message_callback=on_message)
    channel.start_consuming()
