import pika

def setup_dlq(channel, queue_name, max_retries=3):
    """Configura una DLQ (Dead Letter Queue) para un queue."""
    dlq_name = f"{queue_name}.dlq"
    dlq_exchange = f"{queue_name}.dlx"
    
    # Crear exchange para DLQ
    channel.exchange_declare(
        exchange=dlq_exchange,
        exchange_type="direct",
        durable=True
    )
    
    # Crear la DLQ
    channel.queue_declare(
        queue=dlq_name,
        durable=True
    )
    
    # Bindear DLQ al exchange
    channel.queue_bind(
        exchange=dlq_exchange,
        queue=dlq_name,
        routing_key=dlq_name
    )
    
    return dlq_name, dlq_exchange
