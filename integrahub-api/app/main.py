from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .auth import create_token, verify_token
import httpx
import os

app = FastAPI(title="IntegraHub API")

# CORS para Demo Portal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Usuarios hardcodeados (solo para demostración)
USERS = {
    "admin": "password123",
    "user": "pass456"
}

@app.get("/health")
def health():
    """Health check del sistema."""
    return {"status": "ok", "service": "integrahub-api"}

@app.post("/token")
def login(username: str, password: str):
    """
    Endpoint para obtener un JWT token.
    
    Ejemplo:
    - username: "admin"
    - password: "password123"
    """
    if username not in USERS or USERS[username] != password:
        return {"error": "Credenciales inválidas"}
    
    token = create_token({"sub": username})
    return {
        "access_token": token,
        "token_type": "bearer",
        "message": f"Bienvenido {username}!"
    }

@app.get("/protected")
def protected_route(username: str = Depends(verify_token)):
    """
    Ruta protegida que requiere JWT token válido.
    Debes pasar el token en el header: Authorization: Bearer <token>
    """
    return {
        "message": f"Hola {username}, accediste a ruta protegida!",
        "access": "granted"
    }

@app.get("/status")
def system_status():
    """Estado general del sistema con health checks REALES."""
    services = {}
    
    # Check order-service (tiene endpoint HTTP)
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get("http://order-service:8080/health", timeout=2.0)
            services["order-service"] = {"status": "UP", "icon": "✅"} if response.status_code == 200 else {"status": "DOWN", "icon": "❌"}
    except:
        services["order-service"] = {"status": "DOWN", "icon": "❌"}
    
    # Check RabbitMQ y sus consumers
    try:
        with httpx.Client(timeout=3.0) as client:
            # Verificar RabbitMQ Management API
            rabbitmq_auth = ("guest", "guest")
            
            # Check inventory.queue consumers
            try:
                r = client.get("http://rabbitmq:15672/api/queues/%2F/inventory.queue", auth=rabbitmq_auth, timeout=2.0)
                if r.status_code == 200:
                    data = r.json()
                    consumers = data.get("consumers", 0)
                    services["inventory-service"] = {"status": "UP", "icon": "✅", "consumers": consumers} if consumers > 0 else {"status": "DOWN", "icon": "❌", "consumers": 0}
                else:
                    services["inventory-service"] = {"status": "UNKNOWN", "icon": "⚠️"}
            except:
                services["inventory-service"] = {"status": "UNKNOWN", "icon": "⚠️"}
            
            # Check payment.queue consumers
            try:
                r = client.get("http://rabbitmq:15672/api/queues/%2F/payment.queue", auth=rabbitmq_auth, timeout=2.0)
                if r.status_code == 200:
                    data = r.json()
                    consumers = data.get("consumers", 0)
                    services["payment-service"] = {"status": "UP", "icon": "✅", "consumers": consumers} if consumers > 0 else {"status": "DOWN", "icon": "❌", "consumers": 0}
                else:
                    services["payment-service"] = {"status": "UNKNOWN", "icon": "⚠️"}
            except:
                services["payment-service"] = {"status": "UNKNOWN", "icon": "⚠️"}
            
            # Check notification.queue consumers
            try:
                r = client.get("http://rabbitmq:15672/api/queues/%2F/notification.queue", auth=rabbitmq_auth, timeout=2.0)
                if r.status_code == 200:
                    data = r.json()
                    consumers = data.get("consumers", 0)
                    services["notification-service"] = {"status": "UP", "icon": "✅", "consumers": consumers} if consumers > 0 else {"status": "DOWN", "icon": "❌", "consumers": 0}
                else:
                    services["notification-service"] = {"status": "UNKNOWN", "icon": "⚠️"}
            except:
                services["notification-service"] = {"status": "UNKNOWN", "icon": "⚠️"}
                
            services["rabbitmq"] = {"status": "UP", "icon": "✅"}
    except:
        services["rabbitmq"] = {"status": "DOWN", "icon": "❌"}
        services["inventory-service"] = {"status": "UNKNOWN", "icon": "⚠️"}
        services["payment-service"] = {"status": "UNKNOWN", "icon": "⚠️"}
        services["notification-service"] = {"status": "UNKNOWN", "icon": "⚠️"}
    
    # Check PostgreSQL via order-service
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get("http://order-service:8080/inventory", timeout=2.0)
            services["postgres"] = {"status": "UP", "icon": "✅"} if response.status_code == 200 else {"status": "DOWN", "icon": "❌"}
    except:
        services["postgres"] = {"status": "UNKNOWN", "icon": "⚠️"}
    
    return {
        "status": "online",
        "services": services
    }
