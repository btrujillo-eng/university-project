# Canasta Express API

Backend REST para la tienda de legumbrería Canasta Express. Está construido con FastAPI, Pydantic, SQLAlchemy asíncrono y PostgreSQL.

## Requisitos

Antes de iniciar, instala:

- **Python 3.13**.
- **PostgreSQL**.
- **Node.js y npm** (para ejecutar el frontend).
- Una cuenta de Stripe con claves de prueba si quieres probar pagos con tarjeta.
- Una cuenta de Resend si quieres probar correos de recuperación y notificaciones.
- Una aplicación OAuth de Google si quieres probar el inicio de sesión con Google.

## Puesta en marcha local

Los comandos de esta guía se ejecutan desde la raíz del repositorio, salvo que se indique lo contrario.

### 1. Configurar PostgreSQL

Crea una base de datos vacía en PostgreSQL. Después configura las credenciales en `backend/.env` (consulta `backend/.env.example`).

El proyecto separa dos usuarios de PostgreSQL:

- **`DDL_DB_USER` / `DDL_USER_PASSWORD`:** usuario que utiliza Alembic para crear y modificar la estructura de la base de datos: tablas, columnas, índices y demás objetos del esquema. DDL significa *Data Definition Language*.
- **`DML_DB_USER` / `DML_USER_PASSWORD`:** usuario que utiliza la aplicación cuando consulta o modifica los datos durante su funcionamiento: `SELECT`, `INSERT`, `UPDATE` y `DELETE`. DML significa *Data Manipulation Language*.

Lo recomendable es utilizar dos usuarios distintos y conceder al usuario DML únicamente los permisos necesarios para operar sobre los datos. **Para una instalación local de prueba también puedes utilizar el mismo usuario en ambos campos**, siempre que sea el usuario propietario de la base de datos (el usuario con el que creaste esa base de datos). En ese caso, coloca el mismo nombre y contraseña en las variables DDL y DML. No uses un usuario limitado que no tenga permisos para ejecutar las migraciones.

### 2. Configurar las variables de entorno

Crea los archivos locales a partir de las plantillas:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edita ambos archivos y reemplaza los valores de ejemplo por tus propias credenciales. No subas los archivos `.env` al repositorio ni compartas sus secretos.

En `backend/.env`, completa como mínimo:

- Datos de conexión de PostgreSQL: `DB_HOST`, `DB_PORT`, `DB_NAME`.
- Usuarios y contraseñas DDL/DML.
- `JWT_SECRET_KEY`: genera un valor aleatorio propio.
- `STRIPE_API_KEY` y `RESEND_API_KEY` si vas a probar esos servicios.
- `GOOGLE_CLIENT_ID` si vas a probar Google Sign-In.

En `frontend/.env`, revisa `VITE_API_BASE_URL` y `VITE_BACKEND_TARGET` para que el frontend se comunique con el backend local. Completa también las claves públicas de Google o Stripe si vas a utilizar esas integraciones.

### 3. Instalar dependencias del backend

```bash
cd backend
python -m venv .venv
```

Activa el entorno virtual:

**Linux/macOS**
```bash
source .venv/bin/activate
```

**Windows PowerShell**
```powershell
.venv\\Scripts\\Activate.ps1
```

Instala las dependencias:

```bash
python -m pip install -r requirements-prod.txt -r requirements-dev.txt
```

### 4. Crear las tablas, cargar los datos iniciales e iniciar el backend

Asegúrate de que PostgreSQL esté encendido, que la base de datos ya exista y que `backend/.env` tenga los datos correctos. Hay **dos formas de crear las tablas**. Escoge solo una:

#### Opción A: utilizar Alembic (recomendado)

Alembic crea o actualiza la estructura de la base de datos a partir de las migraciones del proyecto. Desde la carpeta `backend/`, ejecuta:

```bash
alembic upgrade head
```

Este comando crea las tablas, columnas, índices y demás objetos definidos en las migraciones. **No ejecutes después `create_db.sql` sobre esa misma base de datos:** ese archivo elimina las tablas existentes antes de crearlas.

Las cuentas y secciones iniciales que aparecen en la sección de datos semilla de `create_db.sql` no se cargan al ejecutar las migraciones. Si eliges Alembic, tendrás que crear los usuarios de prueba y los datos iniciales que necesites por separado.

#### Opción B: ejecutar `create_db.sql` (creación manual)

En la raíz del repositorio se encuentra el archivo `create_db.sql`. Este contiene las sentencias SQL para crear los tipos, tablas, índices y también insertar las secciones y los usuarios de prueba.

Puedes copiarlo directamente a tu directorio personal (`home` en Linux), donde normalmente trabajas con tus archivos:

```bash
cp create_db.sql ~/create_db.sql
```

Luego ejecuta el archivo completo desde la terminal con `psql`. Por ejemplo, si el usuario de PostgreSQL es `app_user`, la base de datos se llama `ecommerce_db` y PostgreSQL está en `127.0.0.1`:

```bash
psql -U app_user -d ecommerce_db -h 127.0.0.1 -f ~/create_db.sql
```

También puedes ejecutarlo mediante la entrada estándar:

```bash
psql -U app_user -d ecommerce_db -h 127.0.0.1 < ~/create_db.sql
```

Sustituye `app_user` y `ecommerce_db` por el usuario y el nombre de la base de datos que configuraste. Si guardaste el archivo en otra ubicación, ajusta la ruta. PostgreSQL puede solicitarte la contraseña del usuario.

**Advertencia:** `create_db.sql` es un script destructivo: elimina las tablas y tipos existentes antes de crearlos de nuevo. Úsalo únicamente en una base de datos local vacía o que puedas borrar por completo. No lo ejecutes sobre una base con información que quieras conservar ni después de haber aplicado las migraciones de Alembic.

#### Datos semilla incluidos en `create_db.sql`

El script inserta las secciones iniciales del catálogo y cinco cuentas de prueba, una por cada rol:

| Rol | Correo |
|---|---|
| Administrador de tienda (`store_manager`) | `admin.tienda@canasta.com` |
| Administrador de bodega (`warehouse_manager`) | `bodega@canasta.com` |
| Encargado de empaque (`packaging_manager`) | `empaque@canasta.com` |
| Domiciliario (`courier`) | `courier@canasta.com` |
| Cliente (`customer`) | `cliente@canasta.com` |

La contraseña de todas estas cuentas de prueba es `usuario123*`. El script almacena el hash bcrypt, no la contraseña en texto plano. Estas cuentas son únicamente para desarrollo local; cambia o elimina estas credenciales antes de cualquier despliegue.

#### Iniciar el backend

Después de crear las tablas con **una** de las dos opciones anteriores, desde la carpeta `backend/` inicia la API:

```bash
uvicorn main:app --reload
```

El backend estará disponible normalmente en `http://127.0.0.1:8000`. La documentación interactiva de la API estará en [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 5. Instalar e iniciar el frontend

Abre otra terminal y, desde la raíz del repositorio, ejecuta:

```bash
cd frontend
npm install
npm run dev
```

Vite mostrará la dirección local del frontend (normalmente [http://localhost:5173](http://localhost:5173)). Abre esa dirección en el navegador.

### 6. Preparar usuarios y datos para probar

La base de datos recién creada no contiene automáticamente productos, secciones ni pedidos. Registra un usuario desde la pantalla de registro o utiliza las cuentas de prueba que se entreguen en el script de datos semilla, si está disponible.

Para probar los distintos paneles, necesitas usuarios con los roles correspondientes:

- `customer`: cliente.
- `store_manager`: administrador de tienda.
- `warehouse_manager`: administrador de bodega.
- `packaging_manager`: encargado de empaque.
- `courier`: domiciliario.

Después de iniciar sesión, prueba los flujos según el rol. Para recorrer el proceso completo de un pedido, crea primero productos y existencias, inicia sesión como cliente y realiza una compra; luego continúa el flujo con los usuarios de tienda, bodega, empaque y domicilio.


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

## Cómo probar las integraciones externas

### Correos y notificaciones con Resend

Configura `RESEND_API_KEY` en `backend/.env` con una API key de tu propia cuenta de [Resend](https://resend.com/).

**Importante para las pruebas:** si tu cuenta todavía no tiene un dominio remitente verificado y estás usando el modo de prueba de Resend, solo podrás enviar correos al correo electrónico asociado/verificado de la cuenta de Resend con la que creaste esa API key. Por tanto, para comprobar la recuperación de contraseña y las notificaciones, registra en Canasta Express ese mismo correo como destinatario. Si intentas enviar a otra dirección, Resend puede rechazar el envío; no significa necesariamente que el flujo del backend esté fallando.

Para enviar a otras direcciones, primero verifica un dominio propio en Resend y configura un remitente permitido para ese dominio. No intentes solucionar esta restricción cambiando únicamente el correo del usuario en la aplicación.

### Pagos con Stripe

Configura una clave secreta de prueba `sk_test_...` en `STRIPE_API_KEY`. Utiliza las tarjetas de prueba de la sección [Tarjetas de prueba de Stripe](#tarjetas-de-prueba-de-stripe). No utilices claves live ni datos de tarjetas reales.

### Inicio de sesión con Google

Configura el mismo OAuth Client ID de tipo aplicación web en el backend y en `frontend/.env`. En Google Cloud Console autoriza el origen local del frontend, normalmente `http://localhost:5173`.

## Pruebas automatizadas

Desde la carpeta `backend/`, con el entorno virtual activado:

```bash
python -m compileall -q app tests main.py scripts
python -m pytest -q
```

GitHub Actions compila, importa la API, ejecuta la migración contra PostgreSQL temporal y ejecuta las pruebas automatizadas.

Para medir rendimiento de autenticación en un entorno de pruebas, desde `backend/` ejecuta `python scripts/performance_auth.py --base-url http://127.0.0.1:8000 --users 60 --runs 3`. El script crea cuentas persistentes y debe usarse solo con una base desechable.

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


#### Tarjetas de prueba de Stripe

Utiliza estas tarjetas exclusivamente con las claves de prueba de Stripe (`sk_test_` y `pk_test_`). No son tarjetas reales y no deben utilizarse en modo producción.

| Resultado esperado | Número de tarjeta | CVV/CVC | Vencimiento |
|---|---|---|---|
| Pago aprobado (Visa) | `4242 4242 4242 4242` | Cualquier 3 dígitos, por ejemplo `123` | Cualquier fecha futura, por ejemplo `12/2030` |
| Pago rechazado | `4000 0000 0000 0002` | Cualquier 3 dígitos, por ejemplo `123` | Cualquier fecha futura |
| Fondos insuficientes | `4000 0000 0000 9995` | Cualquier 3 dígitos, por ejemplo `123` | Cualquier fecha futura |
| Requiere autenticación 3D Secure | `4000 0025 0000 3155` | Cualquier 3 dígitos, por ejemplo `123` | Cualquier fecha futura |

Para estas tarjetas Visa se utiliza un CVC de tres dígitos. En las pruebas, Stripe acepta cualquier fecha futura y cualquier CVC válido para la marca. Para American Express el CVC tiene cuatro dígitos. Consulta la [documentación oficial de Stripe sobre pruebas](https://docs.stripe.com/testing) para más escenarios y marcas de tarjeta.

### Credenciales de servicios externos para el equipo receptor

Cada equipo debe configurar sus propias credenciales de desarrollo y prueba en los archivos `.env`; el repositorio solo debe contener plantillas `.env.example`, nunca secretos reales.

1. **Stripe:** configura `STRIPE_API_KEY` con la clave secreta de prueba (`sk_test_...`) en el backend. Si el frontend usa Stripe.js, configura también la clave publicable (`pk_test_...` o la variable frontend correspondiente). No uses claves live. Utiliza las tarjetas de prueba indicadas arriba para simular pagos aprobados, rechazados y autenticación adicional.
2. **Resend:** crea una API key en [Resend](https://resend.com/) y asígnala a `RESEND_API_KEY`. Configura un remitente/dominio permitido por tu cuenta y utiliza una dirección de correo a la que tengas acceso para comprobar los códigos de recuperación y notificaciones.
3. **Google OAuth:** crea un OAuth 2.0 Client ID de tipo aplicación web en [Google Cloud Console](https://console.cloud.google.com/). Configura ese mismo ID en `GOOGLE_CLIENT_ID` (backend) y `VITE_GOOGLE_CLIENT_ID` (frontend), y autoriza el origen local del frontend, normalmente `http://localhost:5173`.
4. **PostgreSQL y JWT:** completa las variables de conexión, credenciales DDL/DML y `JWT_SECRET_KEY` con valores propios del entorno local. Genera un secreto JWT nuevo; no utilices el marcador de ejemplo.

Antes de probar, inicia PostgreSQL, verifica que las variables estén cargadas y comprueba que el frontend apunte al backend local. Si no configuras Stripe, Resend o Google OAuth, no podrás probar los flujos que dependen de esos servicios. Nunca envíes números de tarjeta ni CVC al backend: el navegador debe tokenizar la tarjeta mediante Stripe.js/Elements y enviar el identificador de método de pago.


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
