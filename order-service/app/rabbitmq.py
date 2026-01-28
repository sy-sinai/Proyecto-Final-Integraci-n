import pika
import json
import os

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")  # nombre del contenedor

def publish_order_created(event: dict):
    # 1. Conectarse a RabbitMQ
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )

    channel = connection.channel()

    # 2. Crear (o asegurar) el exchange
    channel.exchange_declare(
        exchange="orders.exchange",
        exchange_type="topic",
        durable=True
    )

    # 3. Publicar el mensaje
    channel.basic_publish(
        exchange="orders.exchange",
        routing_key="order.created",
        body=json.dumps(event)
    )

    # 4. Cerrar conexión
    connection.close()
