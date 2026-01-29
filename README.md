# IntegraHub - Sistema de Integracion Order-to-Cash

## Descripcion del Sistema

IntegraHub es una plataforma de integracion empresarial que implementa el flujo completo Order-to-Cash para una empresa de retail. El sistema permite:

- Creacion y procesamiento de pedidos via API REST
- Validacion de inventario en tiempo real
- Procesamiento de pagos (simulado)
- Notificaciones de cambios de estado
- Ingesta de archivos CSV para actualizacion de inventario
- Analitica y metricas en tiempo real

### Arquitectura

El sistema esta compuesto por los siguientes microservicios:

| Servicio | Descripcion | Puerto |
|----------|-------------|--------|
| order-service | API REST para gestion de pedidos | 8082 |
| integrahub-api | API principal con autenticacion JWT | 8081 |
| inventory-service | Validacion y reserva de stock | - |
| payment-service | Procesamiento de pagos | - |
| notification-service | Notificaciones de eventos | - |
| file-ingestor | Ingesta de archivos CSV | - |
| analytics-service | Metricas y trazabilidad | 8083 |
| demo-portal | Portal web de demostracion | 3000 |
| PostgreSQL | Base de datos | 5432 |
| RabbitMQ | Broker de mensajeria | 5672/15672 |

---

## Requisitos para Ejecutar

### Software Requerido

- Docker Desktop 4.0 o superior
- Docker Compose v2.0 o superior
- (Opcional) Postman para pruebas de API

### Recursos del Sistema

- Minimo 8 GB de RAM disponible
- 10 GB de espacio en disco
- Puertos disponibles: 3000, 5432, 5672, 8081, 8082, 8083, 15672

### Verificar Instalacion

```bash
docker --version
docker compose version
```

---

## Como Levantar el Sistema

### 1. Clonar o ubicarse en el directorio del proyecto

```bash
cd order-integration-system
```

### 2. Levantar todos los servicios

```bash
docker compose up -d
```

### 3. Verificar que todos los contenedores esten corriendo

```bash
docker compose ps
```

Todos los servicios deben mostrar estado "Up" o "Running".

### 4. Esperar inicializacion

Esperar aproximadamente 30 segundos para que RabbitMQ y PostgreSQL esten completamente listos.

### 5. Detener el sistema

```bash
docker compose down
```

---

## URLs Importantes

### Demo Portal (Interfaz Principal)

```
http://localhost:3000
```

Portal web para crear pedidos, ver inventario, consultar estado del sistema y visualizar metricas.

### Swagger UI - Documentacion de APIs

| API | URL |
|-----|-----|
| Order Service | http://localhost:8082/docs |
| IntegraHub API | http://localhost:8081/docs |
| Analytics Service | http://localhost:8083/docs |

### RabbitMQ Management UI

```
http://localhost:15672
```

Credenciales:
- Usuario: guest
- Password: guest

Permite visualizar colas, exchanges y mensajes en transito.

### Health Checks

| Servicio | URL |
|----------|-----|
| Order Service | http://localhost:8082/health |
| IntegraHub API | http://localhost:8081/health |
| Analytics | http://localhost:8083/health |
| System Status | http://localhost:8081/status |

---

## Pasos Basicos de Prueba

### Flujo A - Creacion y Procesamiento de Pedido (Punto a Punto)

1. Abrir el Demo Portal en http://localhost:3000

2. Verificar que el inventario tenga productos disponibles en la seccion "Inventario Actual"

3. Crear un pedido:
   - Ingresar nombre del cliente
   - Seleccionar un producto del dropdown
   - Ingresar cantidad (menor o igual al stock disponible)
   - Click en "Crear Pedido"

4. Observar el pedido en la tabla "Pedidos":
   - Estado inicial: CREATED
   - Luego de procesamiento: PAID (exitoso) o REJECTED (sin stock)

5. Verificar en Analytics que las metricas se actualicen

Resultado esperado:
- Si hay stock suficiente: Estado final PAID
- Si no hay stock suficiente: Estado final REJECTED

---

### Flujo B - Notificaciones Pub/Sub

1. Crear un pedido desde el Demo Portal

2. Abrir una terminal y ver los logs del notification-service:

```bash
docker logs notification-service --tail 20 -f
```

3. Verificar que aparezcan mensajes indicando la notificacion del estado del pedido

4. Los eventos order.confirmed y order.rejected se publican a multiples consumidores simultaneamente

---

### Flujo C - Integracion por Archivos (Legado)

1. Crear un archivo CSV con el formato requerido:

```csv
sku,name,quantity,price
PROD-001,Producto Nuevo,50,99.99
MOUSE-001,Mouse Logitech MX,10,49.99
```

2. Copiar el archivo a la carpeta inbox:

```bash
copy mi_inventario.csv inbox/
```

3. Esperar 10 segundos (el file-ingestor revisa periodicamente)

4. Verificar los logs del procesamiento:

```bash
docker logs file-ingestor --tail 20
```

5. El archivo procesado se movera a la carpeta "processed" o "error" segun corresponda

6. Verificar en el Demo Portal que el inventario se haya actualizado (las cantidades se SUMAN al stock existente)

---

### Flujo D - Analitica (Streaming)

1. Acceder a las metricas via API:

```bash
curl http://localhost:8083/metrics
```

O abrir en navegador: http://localhost:8083/metrics

2. Verificar metricas disponibles:
   - orders_created: Total de ordenes creadas
   - orders_completed: Ordenes completadas exitosamente
   - inventory_validated: Validaciones de inventario exitosas
   - inventory_rejected: Rechazos por falta de stock
   - payments_successful: Pagos exitosos
   - success_rate: Tasa de exito porcentual

3. Consultar trazabilidad de una orden especifica:

```
http://localhost:8083/events/{order_id}
```

4. Ver todos los eventos recientes:

```
http://localhost:8083/events
```

5. En el Demo Portal, la seccion "Analytics en Tiempo Real" muestra las metricas actualizadas automaticamente

---

## Pruebas de Seguridad (JWT)

### Obtener Token

```bash
curl -X POST "http://localhost:8081/token?username=admin&password=password123"
```

Credenciales disponibles:
- admin / password123
- user / pass456

### Usar Token en Rutas Protegidas

```bash
curl -H "Authorization: Bearer {token}" http://localhost:8081/protected
```

### Probar Token Invalido

```bash
curl -H "Authorization: Bearer token_invalido" http://localhost:8081/protected
```

Resultado esperado: Error 401 Unauthorized

---

## Pruebas de Resiliencia

### Simular Caida de Servicio

1. Detener el inventory-service:

```bash
docker compose stop inventory-service
```

2. Crear un pedido desde el Demo Portal

3. Verificar que el pedido queda en estado CREATED (no se procesa)

4. Verificar en el Demo Portal que System Status muestra inventory-service como DOWN

5. Levantar el servicio nuevamente:

```bash
docker compose start inventory-service
```

6. El pedido pendiente se procesara automaticamente (mensajes en cola)

### Ver Dead Letter Queue

En RabbitMQ UI (http://localhost:15672):
- Navegar a Queues
- Buscar colas con sufijo ".dlq"
- Contienen mensajes que fallaron despues de multiples reintentos

---

## Coleccion Postman

Importar el archivo para pruebas completas:

```
docs/IntegraHub.postman_collection.json
```

La coleccion incluye:
- Autenticacion (happy path y error)
- CRUD de ordenes
- Consulta de inventario
- Health checks
- Metricas de analytics

---

## Estructura del Proyecto

```
order-integration-system/
├── docker-compose.yml
├── README.md
├── order-service/          # API de pedidos
├── integrahub-api/         # API con autenticacion
├── inventory-service/      # Validacion de stock
├── payment-service/        # Procesamiento de pagos
├── notification-service/   # Notificaciones
├── file-ingestor/          # Ingesta de CSV
├── analytics-service/      # Metricas y eventos
├── demo-portal/            # Portal web
├── docs/                   # Documentacion y Postman
├── inbox/                  # Carpeta entrada CSV
├── processed/              # CSV procesados
└── error/                  # CSV con errores
```

---

## Patrones de Integracion Implementados

1. Point-to-Point: Colas dedicadas (inventory.queue, payment.queue)
2. Publish/Subscribe: Exchange tipo topic con multiples consumidores
3. Message Router: Routing keys para dirigir mensajes (order.created, order.validated)
4. Message Translator: Transformacion entre DTOs y eventos de dominio
5. Dead Letter Channel: Colas DLQ para mensajes fallidos
6. Idempotent Consumer: Tabla de mensajes procesados para evitar duplicados

---

Proyecto desarrollado para el curso de Integracion de Sistemas.
