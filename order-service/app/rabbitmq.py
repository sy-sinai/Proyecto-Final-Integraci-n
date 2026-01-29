import pika
import json
import os
from uuid import uuid4
import logging
from .circuit_breaker import CircuitBreaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
EXCHANGE = "orders.exchange"

# Circuit breaker para RabbitMQ
circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=30)

def publish_order_created(order_id: int, order_data: dict):
    """Publica evento OrderCreated a RabbitMQ con timeout y circuit breaker."""
    def _publish():
        try:
            # Conexión con timeout
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    socket_timeout=5.0,  # 5 segundos timeout
                    connection_attempts=3
                )
            )
            channel = connection.channel()

            # Asegurar exchange
            channel.exchange_declare(
                exchange=EXCHANGE,
                exchange_type="topic",
                durable=True
            )

            # Crear evento
            correlation_id = str(uuid4())
            event = {
                "event_type": "OrderCreated",
                "correlation_id": correlation_id,
                "order_id": order_id,
                **order_data
            }

            # Publicar
            channel.basic_publish(
                exchange=EXCHANGE,
                routing_key="order.created",
                body=json.dumps(event),
                properties=pika.BasicProperties(delivery_mode=2)
            )

            logger.info(f"✅ Evento publicado: order_id={order_id}")
            connection.close()
            return correlation_id

        except Exception as e:
            logger.error(f"❌ Error publicando evento: {e}")
            raise
    
    # Usar circuit breaker
    return circuit_breaker.call(_publish)
