import json
import pika

RABBITMQ_HOST = "rabbitmq"
EXCHANGE = "orders.exchange"

def publish_inventory_result(order_id: int, status: str):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type="topic",
        durable=True
    )

    event = {
        "event_type": "InventoryResult",
        "order_id": order_id,
        "status": status
    }

    routing_key = "order.validated" if status == "VALIDATED" else "order.rejected"

    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=routing_key,
        body=json.dumps(event).encode("utf-8"),
        properties=pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2  # persistente
        )
    )

    connection.close()
