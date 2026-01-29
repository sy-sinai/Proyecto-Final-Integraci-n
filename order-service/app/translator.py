"""
Message Translator - Patrón de integración para transformar mensajes entre formatos.
Convierte DTOs internos a eventos de dominio y viceversa.
"""
from typing import Dict, Any
from datetime import datetime

class OrderEventTranslator:
    """Traduce entre modelos de Order y eventos de mensajería."""
    
    @staticmethod
    def order_to_created_event(order_id: int, order_data: dict, correlation_id: str) -> Dict[str, Any]:
        """Transforma Order DB model → OrderCreated Event."""
        return {
            "event_type": "OrderCreated",
            "correlation_id": correlation_id,
            "order_id": order_id,
            "product": order_data.get("product"),
            "quantity": order_data.get("quantity"),
            "customer_name": order_data.get("customer_name"),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def inventory_result_event(order_id: int, status: str) -> Dict[str, Any]:
        """Crea evento de resultado de inventario."""
        return {
            "event_type": "InventoryResult",
            "order_id": order_id,
            "status": status,  # VALIDATED o REJECTED
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def payment_result_event(order_id: int, status: str) -> Dict[str, Any]:
        """Crea evento de resultado de pago."""
        return {
            "event_type": "PaymentResult",
            "order_id": order_id,
            "status": status,  # PAID o FAILED
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def event_to_order_update(event: dict) -> Dict[str, Any]:
        """Extrae datos relevantes de un evento para actualizar Order."""
        return {
            "order_id": event.get("order_id"),
            "status": event.get("status"),
            "event_type": event.get("event_type")
        }


class InventoryTranslator:
    """Traduce entre CSV de inventario y modelo de BD."""
    
    @staticmethod
    def csv_row_to_inventory(row: dict) -> Dict[str, Any]:
        """Transforma fila CSV → InventoryItem."""
        return {
            "sku": str(row.get("sku", "")).strip(),
            "name": str(row.get("name", "")).strip(),
            "quantity": int(row.get("quantity", 0)),
            "price": float(row.get("price", 0.0))
        }
    
    @staticmethod
    def inventory_to_api_response(item) -> Dict[str, Any]:
        """Transforma InventoryItem DB → API Response."""
        return {
            "sku": item.sku,
            "name": item.name,
            "quantity": item.quantity,
            "price": item.price,
            "available": item.quantity > 0
        }
