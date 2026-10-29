# Canasta Express API

Backend REST para la tienda de legumbrería Canasta Express. Está construido con FastAPI, Pydantic, SQLAlchemy asíncrono y PostgreSQL.

## Requisitos y configuración

- Python 3.13 y PostgreSQL.
- Claves de prueba de Stripe y Resend para probar las integraciones externas.
- Instala dependencias con `python -m pip install -r requirements-prod.txt -r requirements-dev.txt`.
- Configura en `.env` las variables de base de datos, Stripe, Resend y JWT. No subas secretos al repositorio.
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

- Usuarios: registro, inicio de sesión JWT y restauración de contraseña por correo.
- Catálogo: `GET /products/` con filtros opcionales `search` y `section_id`; `POST /products/` para el administrador de tienda.
- Precio: `PATCH /products/{product_id}/price` (administrador de tienda).
- Stock: `PATCH /products/{product_id}/stock` (administrador de bodega).
- Carrito: `GET /cart/`, `POST /cart/items`, `DELETE /cart/items/{product_id}`.
- Checkout: `POST /orders/checkout`; valida stock y mínimo de COP 20.000.
- Pedidos: historial del cliente, consulta y confirmación de empaque, asignación de domiciliario, estados de entrega y confirmación de efectivo.

Los productos incluyen `image_path` tanto en el resultado de `GET /products/` como en la respuesta de creación/actualización. El frontend debe usar esa ruta para mostrar la imagen; si se sirve desde otro origen, debe resolver la ruta contra la URL base de la API.

## Pruebas y CI

```bash
python -m compileall -q app tests main.py scripts
python -m pytest -q
```

GitHub Actions compila, importa la API, ejecuta la migración contra PostgreSQL temporal y ejecuta las pruebas automatizadas.

Para medir rendimiento de autenticación en un entorno de pruebas, ejecuta `python scripts/performance_auth.py --base-url http://127.0.0.1:8000 --users 60 --runs 3`. El script crea cuentas persistentes y debe usarse solo con una base desechable.

## Limitaciones conocidas

- El cobro con Stripe y la persistencia del pedido no comparten una transacción distribuida; producción requiere idempotencia y reconciliación/outbox.
- La integración Stripe actual usa tokens de prueba; antes de producción, el frontend debe tokenizar con Stripe.js y el backend no debe recibir ni almacenar número completo de tarjeta ni CVV.
- La CI no sustituye pruebas reales con credenciales de Stripe/Resend ni pruebas de carga en el entorno desplegado.


## Contratos ampliados para los mockups

- `GET /products/sections` devuelve `id` y `name` de cada sección para llenar selectores.
- `GET /products/?search=...` busca por nombre del producto o nombre de la sección; también admite `section_id`. Los productos incluyen `section_name` e `image_path`.
- `CheckoutRequest.shipping` recibe `street`, `neighborhood`, `department`, `details`, `delivery_instructions` (opcional), `city` y `phone_number`.
- Los pedidos y artículos ahora incluyen nombre del cliente, datos de domicilio, teléfono e `image_path` por artículo. El recibo digital incluye los datos del comprador y el desglose subtotal/envío/total.
- El costo de envío está actualmente fijado en COP 0.00 porque no existe una tarifa definida en los requisitos. Cambia `SHIPPING_COST` cuando se acuerde una regla de negocio; no uses el valor de presentación como fuente de verdad.
- Para compatibilidad con registros previos, la migración agrega los nuevos campos con valores por defecto vacíos. Los pedidos antiguos no recuperan mágicamente barrio/departamento; deben actualizarse si necesitas mostrar esos datos históricos.
