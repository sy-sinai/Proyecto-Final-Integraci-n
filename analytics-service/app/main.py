import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models import SessionLocal, OrderEvent, Metrics
from app.consumer import start_consumer
from sqlalchemy import func

app = FastAPI(title="Analytics Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    """Inicia el consumer en un thread separado."""
    thread = threading.Thread(target=start_consumer, daemon=True)
    thread.start()
    print("🚀 Analytics API + Consumer iniciados")

@app.get("/health")
def health():
    return {"status": "ok", "service": "analytics-service"}

@app.get("/metrics")
def get_metrics():
    """Retorna todas las métricas en tiempo real."""
    db = SessionLocal()
    try:
        metrics = db.query(Metrics).all()
        result = {m.metric_name: m.metric_value for m in metrics}
        
        # Calcular tasa de éxito
        created = result.get("orders_created", 0)
        completed = result.get("orders_completed", 0)
        result["success_rate"] = round((completed / created * 100), 2) if created > 0 else 0
        
        return {
            "metrics": result,
            "summary": {
                "total_orders": int(created),
                "completed": int(completed),
                "rejected": int(result.get("inventory_rejected", 0) + result.get("payments_failed", 0)),
                "success_rate": f"{result['success_rate']}%"
            }
        }
    finally:
        db.close()

@app.get("/events")
def get_events(limit: int = 50):
    """Retorna los últimos eventos procesados."""
    db = SessionLocal()
    try:
        events = db.query(OrderEvent).order_by(OrderEvent.timestamp.desc()).limit(limit).all()
        return [
            {
                "id": e.id,
                "order_id": e.order_id,
                "event_type": e.event_type,
                "status": e.status,
                "correlation_id": e.correlation_id,
                "timestamp": e.timestamp.isoformat()
            }
            for e in events
        ]
    finally:
        db.close()

@app.get("/events/{order_id}")
def get_order_events(order_id: int):
    """Retorna todos los eventos de una orden específica (trazabilidad)."""
    db = SessionLocal()
    try:
        events = db.query(OrderEvent).filter(OrderEvent.order_id == order_id).order_by(OrderEvent.timestamp).all()
        return {
            "order_id": order_id,
            "events": [
                {
                    "event_type": e.event_type,
                    "status": e.status,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in events
            ]
        }
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

