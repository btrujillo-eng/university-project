# Canasta Express API

Backend REST para la tienda de legumbrería Canasta Express. Está construido con FastAPI, Pydantic, SQLAlchemy asíncrono y PostgreSQL.

## Requisitos y configuración

- Python 3.13 y PostgreSQL.
- Claves de prueba de Stripe y Resend para probar las integraciones externas.
- Instala dependencias con `python -m pip install -r requirements-prod.txt -r requirements-dev.txt`.
- Configura en `.env` las variables de base de datos, Stripe, Resend y JWT. Para habilitar Google Sign-In, agrega `GOOGLE_CLIENT_ID` con el ID de cliente OAuth 2.0 de tu aplicación web. No subas secretos al repositorio.
- En una base vacía, ejecuta `alembic upgrade head`; después inicia con `uvicorn main:app --reload`.
- La documentación interactiva queda en `/docs`.

## Imágenes de productos y Docker

El endpoint de creación de productos recibe ahora un formulario `multipart/form-data` con los campos `name`, `section_id`, `price`, `stock`, `unit_of_measure` y el archivo obligatorio `image`. Solo acepta JPEG, PNG o WebP hasta 5 MiB. El backend genera un nombre aleatorio, guarda la imagen en `MEDIA_ROOT/products` y persiste en `Product.image_path` la ruta pública, por ejemplo `/media/products/ab12....webp`. El cliente puede usar esa ruta como `src` de la imagen del producto; el backend sirve el archivo en `GET /media/products/{filename}`.

Por defecto `MEDIA_ROOT=media`. En Docker, monta un volumen persistente en la ruta que configures como `MEDIA_ROOT`, por ejemplo:

```yaml
services:
  api:
    environment:
      MEDIA_ROOT: /app/media
    volumes:
      - product_media:/app/media

volumes:
  product_media:
```

El volumen debe persistir entre recreaciones de contenedores y ser compartido por todas las réplicas que sirvan imágenes. Haz backup de ese volumen. No montes la carpeta de imágenes en un directorio público de escritura arbitraria. Las imágenes existentes deben migrarse al volumen antes de desplegar si ya hay registros con rutas guardadas.

Ejemplo de creación desde el navegador:

```javascript
const form = new FormData();
form.append("name", "Tomate chonto");
form.append("section_id", "1");
form.append("price", "4500.00");
form.append("stock", "20");
form.append("unit_of_measure", "kilogram");
form.append("image", selectedFile);
const response = await fetch("/products/", {
  method: "POST",
  headers: { Authorization: `Bearer ${token}` },
  body: form
});
```

No establezcas manualmente el header `Content-Type`: el navegador debe agregar el boundary del multipart.

## Endpoints principales

- Usuarios: registro, inicio de sesión con correo/contraseña, inicio de sesión con Google (`POST /users/v1/auth/google`, JSON `{ "id_token": "<Google ID token>" }`) y restauración de contraseña por correo mediante un código de seis dígitos, válido durante 10 minutos. El frontend debe obtener el ID token con Google Identity Services; el backend valida firma, audiencia y correo verificado antes de emitir su propio JWT. Las cuentas Google nuevas usan el rol `customer`. No se vincula automáticamente una cuenta existente por coincidencia de correo.
- Catálogo: `GET /products/` con filtros opcionales `search`, `section_id`, `limit` (1–100, predeterminado 50) y `offset`; `POST /products/` para el administrador de tienda.
- Precio: `PATCH /products/{product_id}/price` (administrador de tienda).
- Stock: `PATCH /products/{product_id}/stock` (administrador de bodega).
- Carrito: `GET /cart/`, `POST /cart/items`, `DELETE /cart/items/{product_id}`.
- Checkout: `POST /orders/checkout`; requiere el header `Idempotency-Key` con una clave única por intento lógico (por ejemplo, `crypto.randomUUID()`). Reutiliza la misma clave solo al reintentar exactamente el mismo checkout tras un timeout o error de red; para un nuevo intento después de un pago rechazado, genera otra clave. Valida stock y mínimo de COP 20.000. Stripe recibe la misma clave para evitar crear un segundo PaymentIntent si se reintenta la misma solicitud. Si el pedido ya quedó persistido, repetir la clave devuelve `409` con el ID del pedido; consulta el historial para obtener su detalle. Es el único punto de entrada público para procesar un pago; el endpoint genérico `/payments/` se retiró para impedir que el cliente enviara importes arbitrarios fuera de un pedido validado.
- Pedidos: historial del cliente, consulta y confirmación de empaque, asignación de domiciliario, estados de entrega y confirmación de efectivo. Los listados aceptan `limit` (1–100, predeterminado 50) y `offset` para paginar.

Los descuentos del checkout no se aceptan desde el cliente: mientras no exista una regla de elegibilidad validada en el servidor, se aplica `no_aplica`. Las cantidades de carrito y pedido admiten hasta tres decimales para soportar pesos fraccionarios (por ejemplo, 1.5 kg); los productos vendidos por unidad solo aceptan cantidades enteras. El stock también admite tres decimales. Los productos incluyen `image_path` tanto en el resultado de `GET /products/` como en la respuesta de creación/actualización. El frontend debe usar esa ruta para mostrar la imagen; si se sirve desde otro origen, debe resolver la ruta contra la URL base de la API.

## Pruebas y CI

```bash
python -m compileall -q app tests main.py scripts
python -m pytest -q
```

GitHub Actions compila, importa la API, ejecuta la migración contra PostgreSQL temporal y ejecuta las pruebas automatizadas.

Para medir rendimiento de autenticación en un entorno de pruebas, ejecuta `python scripts/performance_auth.py --base-url http://127.0.0.1:8000 --users 60 --runs 3`. El script crea cuentas persistentes y debe usarse solo con una base desechable.

## Limitaciones conocidas

- Stripe y PostgreSQL no comparten una transacción distribuida. El header `Idempotency-Key` evita repetir un PaymentIntent para la misma clave de usuario, incluso si la primera solicitud falla al persistir el pedido; la aplicación aún requiere reconciliación operativa de pagos huérfanos antes de producción.
- La integración Stripe actual usa tokens de prueba; antes de producción, el frontend debe tokenizar con Stripe.js y el backend no debe recibir ni almacenar número completo de tarjeta ni CVV.
- La CI no sustituye pruebas reales con credenciales de Stripe/Resend ni pruebas de carga en el entorno desplegado.


## Contratos ampliados para los mockups

- `GET /products/sections` devuelve `id` y `name` de cada sección para llenar selectores.
- `GET /products/?search=...` busca por nombre del producto o nombre de la sección; también admite `section_id`. Los productos incluyen `section_name` e `image_path`.
- `CheckoutRequest.shipping` recibe `street`, `neighborhood`, `department`, `details`, `delivery_instructions` (opcional), `city` y `phone_number`.
- Los pedidos y artículos ahora incluyen nombre del cliente, datos de domicilio, teléfono e `image_path` por artículo. El recibo digital incluye los datos del comprador y el desglose subtotal/envío/total.
- El costo de envío está actualmente fijado en COP 0.00 porque no existe una tarifa definida en los requisitos. Cambia `SHIPPING_COST` cuando se acuerde una regla de negocio; no uses el valor de presentación como fuente de verdad.
- Para compatibilidad con registros previos, la migración agrega los nuevos campos con valores por defecto vacíos. Los pedidos antiguos no recuperan mágicamente barrio/departamento; deben actualizarse si necesitas mostrar esos datos históricos.


### Integración segura de tarjeta

El checkout con tarjeta recibe `payment_method_id` de Stripe (un ID `pm_...` generado mediante Stripe.js/Elements en el navegador). No envíes `card_number` ni `cvv` al backend. El gateway crea un PaymentIntent y registra en la respuesta únicamente la marca y los últimos cuatro dígitos de la tarjeta. La integración debe probarse con claves y métodos de pago de prueba de Stripe antes de conectar el frontend.


### Cambios de esquema para Google Sign-In

La revisión Alembic `20261029_03` permite `users.password_hash` nulo y agrega `users.google_sub` nullable con índice único. Los usuarios locales conservan su hash; las cuentas Google pueden no tener contraseña local. Ejecuta `alembic upgrade head` después de respaldar la base de datos. Si aplicas el cambio manualmente, usa la misma columna e índice para que la migración no duplique el esquema.


### Roles y flujo de estados de entrega

El backend valida cada operación según el rol autenticado; ocultar botones en el frontend no sustituye estos controles:

- `customer`: consulta su propio historial y realiza checkout/carrito. No puede consultar pedidos de otros clientes ni modificar estados.
- `store_manager`: registra productos, actualiza precios, consulta pedidos empacados en `GET /orders/ready-for-assignment`, consulta domiciliarios activos en `GET /orders/couriers` y asigna domiciliarios a pedidos empacados.
- `warehouse_manager`: actualiza existencias. No puede empacar ni asignar domiciliarios.
- `packaging_manager`: consulta la cola de pedidos `pending` y confirma el empaque. También puede consultar por separado los pedidos `returned_to_warehouse` para volver a empacarlos.
- `courier`: solo consulta pedidos asignados a su propio usuario. Puede moverlos de `packaged` a `in_transit`; desde `in_transit` puede confirmar `delivered` o `returned_to_warehouse`. No puede cancelar pedidos, marcar pedidos como empacados ni asignarse pedidos.

Cuando un domiciliario devuelve un pedido a bodega, el backend elimina la asignación anterior. El encargado de empaque debe volver a empacarlo y el administrador de tienda debe asignarlo nuevamente. El pago en efectivo solo puede confirmarse por el domiciliario asignado mientras el pedido está `in_transit`; el backend exige que se confirme antes de marcar el pedido como `delivered`. Los pagos con tarjeta no pueden modificarse desde ese endpoint.

Para actualizar la entrega, el cliente HTTP debe enviar JSON, por ejemplo:

```json
{ "delivery_status": "returned_to_warehouse" }
```

a `PATCH /orders/{order_id}/delivery-status`. El backend rechaza cualquier transición que no esté permitida, aunque el valor exista en el enum de PostgreSQL. La cola de empaque pendiente se obtiene en `GET /orders/packaging/pending`; las devoluciones se consultan en `GET /orders/packaging/returned`. El endpoint `GET /orders/courier/assigned` incluye `allowed_delivery_statuses` por pedido para que la interfaz muestre únicamente las acciones disponibles, sin reemplazar la validación del servidor.
