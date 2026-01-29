import time
from datetime import datetime

class CircuitBreaker:
    """Simple Circuit Breaker para proteger contra fallos cascada."""
    
    def __init__(self, failure_threshold=5, timeout=60):
        """
        Args:
            failure_threshold: Número de fallos antes de abrir el circuito
            timeout: Segundos antes de intentar recuperar
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        """Ejecuta función con protección de circuit breaker."""
        
        # Si está OPEN y pasó el timeout, intentar HALF_OPEN
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                print(f"🔄 Circuit Breaker en HALF_OPEN, intentando recuperar...")
            else:
                raise Exception("Circuit Breaker OPEN - Servicio no disponible")
        
        try:
            result = func(*args, **kwargs)
            # Si funciona, resetear
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                print("✅ Circuit Breaker CLOSED - Servicio recuperado")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                print(f"🔴 Circuit Breaker OPEN - {self.failure_count} fallos")
            
            raise e
