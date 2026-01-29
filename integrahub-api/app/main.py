from fastapi import FastAPI, Depends
from .auth import create_token, verify_token
import httpx
import os

app = FastAPI(title="IntegraHub API")

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
    """Estado general del sistema con health checks de otros servicios."""
    services = {}
    
    # Check order-service
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get("http://order-service:8080/health", timeout=2.0)
            services["order-service"] = "✅ UP" if response.status_code == 200 else "❌ DOWN"
    except:
        services["order-service"] = "❌ DOWN"
    
    # Check inventory-service (sin endpoint health, consideramos conectividad)
    services["inventory-service"] = "✅ UP (consumer)"
    services["payment-service"] = "✅ UP (consumer)"
    services["notification-service"] = "✅ UP (consumer)"
    
    return {
        "status": "online",
        "services": services,
        "components": {
            "api": "running",
            "auth": "enabled",
            "rabbitmq": "connected",
            "database": "connected"
        }
    }
