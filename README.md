# Canasta Express API

Backend REST para la tienda de legumbrería Canasta Express. Está construido con FastAPI, Pydantic, SQLAlchemy asíncrono y PostgreSQL.

## Requisitos

- Python 3.13
- PostgreSQL
- Claves de Stripe y Resend para probar los flujos externos de pago y correo

## Configuración local

1. Crear y activar un entorno virtual.
2. Instalar dependencias:

   ```bash
   python -m pip install -r requirements-prod.txt -r requirements-dev.txt
   ```

3. Crear un archivo `.env` con las variables requeridas:

   ```dotenv
   STRIPE_API_KEY=sk_test_...
   RESEND_API_KEY=re_...
   DEBUG=false
   MIGRATOR_DB_URL=postgresql+psycopg://usuario_migraciones:contraseña@localhost:5432/canasta_express
   DB_USER=usuario_app
   DB_PASSWORD=contraseña_app
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=canasta_express
   JWT_SECRET_KEY=cambiar-por-un-secreto-largo
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

   Usa claves de prueba para Stripe y Resend. No subas el archivo `.env` al repositorio.

4. En una base de datos vacía, aplicar la migración inicial:

   ```bash
   alembic upgrade head
   ```

   Si la base de datos ya contiene exactamente el esquema inicial, revisa primero su estructura; no ejecutes la migración inicial encima de tablas existentes. Si el esquema existente coincide, se puede registrar el estado inicial con `alembic stamp head`.

5. Iniciar la API:

   ```bash
   uvicorn main:app --reload
   ```

La documentación interactiva de la API estará disponible en `/docs`.

## Funcionalidades implementadas

### Usuarios y autenticación

- Registro e inicio de sesión con JWT.
- Restauración de contraseña por código enviado por correo.
- La respuesta al solicitar un código no revela si el correo está registrado.

### Catálogo e inventario

- `GET /products/`: listar productos; acepta `search` para buscar por nombre y `section_id` para filtrar por sección.
- `POST /products/`: registrar producto (administrador de tienda).
- `PATCH /products/{product_id}/price`: actualizar precio (administrador de tienda).
- `PATCH /products/{product_id}/stock`: actualizar stock (administrador de bodega).

### Carrito

- `GET /cart/`: consultar productos y total calculado con precios actuales.
- `POST /cart/items`: agregar una cantidad al carrito del cliente autenticado.
- `DELETE /cart/items/{product_id}`: eliminar un producto del carrito.
- El servidor valida cantidades positivas y disponibilidad de stock.

### Checkout, pagos y pedidos

- `POST /orders/checkout`: validar el carrito, comprobar stock bajo bloqueo transaccional, exigir un mínimo de COP 20.000, registrar dirección de entrega y procesar tarjeta o efectivo.
- El pago en efectivo queda pendiente y devuelve instrucciones para pagar al recibir el pedido.
- Para pagos con tarjeta aprobados, la respuesta incluye un recibo digital; no se genera recibo cuando el pago con tarjeta falla.
- `GET /orders/me`: historial del cliente autenticado.
- `GET /orders/packaging` y `GET /orders/packaging/pending`: consulta de pedidos por el personal de empaque.
- `POST /orders/{order_id}/packaged`: confirmar empaque.
- `POST /orders/{order_id}/assign-courier/{courier_id}`: asignar un pedido empacado a un domiciliario.
- `GET /orders/courier/assigned`: pedidos asignados al domiciliario autenticado.
- `PATCH /orders/{order_id}/delivery-status?new_status=in_transit`: registrar salida a entrega; después se puede usar `new_status=delivered`.
- `PATCH /orders/{order_id}/cash-payment`: confirmar pago en efectivo recibido por el domiciliario.

Los endpoints protegidos verifican el JWT y el rol correspondiente. Los cambios de estado de entrega siguen transiciones permitidas y los domiciliarios solo pueden modificar pedidos asignados a ellos.

## Pruebas y CI

Ejecutar las pruebas localmente:

```bash
python -m compileall -q app tests main.py
python -m pytest -q
```

GitHub Actions ejecuta compilación, importación de la aplicación y configuración de mapeos ORM, y pruebas unitarias en cada push a la rama de trabajo.

## Nota técnica

El cobro con Stripe y la persistencia del pedido no comparten una transacción distribuida. Para un despliegue productivo conviene añadir idempotencia de pagos y un patrón outbox/reconciliación para gestionar el caso excepcional en que Stripe apruebe el cobro pero falle la persistencia posterior.
