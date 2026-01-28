FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Ejecutar como módulo para que "app" sea un paquete importable siempre
CMD ["python", "-u", "-m", "app.main"]

