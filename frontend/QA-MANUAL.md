# Guía de pruebas manuales — Canasta Express

Esta guía sirve para validar el frontend contra el backend y PostgreSQL locales. La compilación de CI no sustituye estas pruebas de integración manuales.

## 1. Preparación

1. Actualiza la rama `main` y sigue las instrucciones de `frontend/README.md`.
2. Inicia PostgreSQL y aplica las migraciones del backend.
3. Inicia FastAPI y comprueba `/docs` y `/health` (si está habilitado).
4. En `frontend/.env`, configura:
   - `VITE_API_BASE_URL=/backend` para usar el proxy de Vite.
   - `VITE_BACKEND_TARGET=http://127.0.0.1:8000` si FastAPI escucha en esa dirección.
   - `VITE_GOOGLE_CLIENT_ID` si vas a probar Google Identity.
   - `VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...` si vas a probar tarjeta.
5. Ejecuta `npm ci`, `npm run build` y `npm run dev`.

No uses claves `sk_...` de Stripe en el frontend.

## 2. Autenticación — MK-001 a MK-004

- [ ] MK-001: iniciar sesión con credenciales válidas y verificar que el backend devuelve un token y `GET /me/` resuelve el rol correcto.
- [ ] Probar contraseña incorrecta, usuario inactivo y correo inválido; verificar que se muestra el error sin perder el formulario.
- [ ] Activar “Recordar sesión”, recargar la página y verificar que se restaura la sesión. Repetir sin activar la opción y verificar que no persiste.
- [ ] MK-002: registrar un usuario con los campos obligatorios y opcionales; verificar en PostgreSQL que el rol se asignó en backend como `customer`.
- [ ] Probar nombres con menos de 3 caracteres, más de los límites del esquema y correo duplicado.
- [ ] Probar el botón oficial de Google con un Client ID válido; verificar token y perfil. Sin Client ID debe mostrarse un error de configuración.
- [ ] MK-003: solicitar código, verificar que llega el correo, introducir seis dígitos incorrectos, expirados y correctos; probar reenvío.
- [ ] MK-004: establecer contraseña, intentar confirmación distinta, completar el cambio y comprobar que la contraseña anterior ya no autentica.

## 3. Cliente — MK-018 y MK-019

- [ ] Iniciar sesión con un usuario `customer`; verificar catálogo, búsqueda por producto/sección e imágenes servidas desde `/media`.
- [ ] Agregar productos por kg, g, lb y unidad; probar cantidad cero, superior al stock y stock agotado.
- [ ] Abrir carrito, verificar cantidad, precio unitario y subtotal contra PostgreSQL; eliminar un producto y recargar para verificar persistencia.
- [ ] Intentar checkout con carrito vacío, total menor a COP 20.000 y stock insuficiente.
- [ ] Completar dirección con teléfono de 10 dígitos y verificar validaciones.
- [ ] Pago en efectivo: comprobar pedido creado, pago pendiente, carrito vaciado y pedido visible en historial.
- [ ] Pago con Stripe en modo test: usar una tarjeta de prueba de Stripe, comprobar resultado de pago, stock decrementado, pedido e historial. Probar una tarjeta rechazada y una que requiera autenticación adicional.
- [ ] Repetir el mismo checkout por reintento/red de forma que conserve la misma clave de idempotencia; debe evitarse crear o cobrar dos pedidos.
- [ ] MK-019: abrir detalle desde historial y comparar dirección, artículos, cantidades, subtotal, envío y total con el pedido persistido.

## 4. Administrador — MK-016, MK-017 y MK-026

- [ ] Iniciar sesión como `store_manager`; comprobar catálogo y sección de asignación.
- [ ] MK-026: crear producto con sección existente, precio, stock, unidad e imagen JPEG/PNG/WebP; verificar registro y archivo en el volumen de medios.
- [ ] Probar archivo mayor a 5 MB, MIME no permitido y ausencia de imagen.
- [ ] MK-016: buscar por nombre y sección y comprobar disponibilidad/imagen.
- [ ] MK-017: modificar precio y comprobar persistencia; cancelar la edición y verificar que no cambia.
- [ ] Asignar un pedido empacado a un domiciliario activo y comprobar que desaparece de la lista pendiente.

## 5. Bodega — interfaz de inventario

- [ ] Iniciar sesión como `warehouse_manager`; verificar consulta y búsqueda de productos.
- [ ] Actualizar existencias y comprobar persistencia y reflejo en catálogo.
- [ ] Intentar valor negativo, decimal no válido para unidad y producto inexistente.

## 6. Empaque — MK-020 y MK-021

- [ ] Iniciar sesión como `packaging_manager`; comprobar pedidos pendientes y devueltos.
- [ ] Abrir pedido y verificar cliente, dirección, teléfono, pago y artículos contra el pedido real.
- [ ] Marcar empacado; verificar que el pedido pasa a asignación del administrador.
- [ ] Intentar empacar un pedido que ya esté en tránsito; backend debe rechazarlo.

## 7. Domiciliario — MK-022 a MK-025

- [ ] Iniciar sesión como `courier`; verificar que solo aparecen pedidos asignados a ese usuario.
- [ ] Abrir detalle y comprobar dirección, referencia, teléfono, cliente y valor a cobrar.
- [ ] Iniciar entrega y verificar transición a `in_transit`.
- [ ] En efectivo, intentar marcar entregado sin confirmar cobro; backend debe rechazarlo.
- [ ] Confirmar efectivo recibido y luego marcar entregado.
- [ ] Reportar devolución a bodega y comprobar que el pedido deja de estar asignado al domiciliario.
- [ ] Probar acceso a pedido asignado a otro domiciliario; backend debe devolver 403.

## 8. Comprobaciones transversales

- [ ] Abrir la aplicación en escritorio y móvil; comprobar que no hay desbordamiento horizontal.
- [ ] Verificar que los roles no pueden ejecutar operaciones de otros roles (403).
- [ ] Comprobar estados vacíos, carga, errores de red y botones durante operaciones en curso.
- [ ] Revisar en DevTools que no se envían PAN/CVC al backend y que no hay claves secretas expuestas.

## Diferencias conocidas frente a los mockups

- MK-020/021 muestran una tabla de pedidos y una lista de verificación por producto; la pantalla implementada usa lista y panel de detalle, y confirma el empaque a nivel de pedido.
- MK-022/023/024/025 muestran tarjetas de entrega y ventanas modales para dirección, cobro y estado; la pantalla implementada usa lista y panel de detalle.
- MK-025 incluye estados “Cliente ausente” y “Pedido recogido en CD y en camino”; el enum y las transiciones actuales del backend no los contemplan. No se deben simular desde el frontend hasta definir e implementar esas transiciones en backend y base de datos.
- El checkout con tarjeta debe probarse con claves Stripe de test. Los pagos que requieren autenticación 3DS adicional necesitan validación específica; el backend actual confirma el PaymentIntent en servidor y no devuelve un client secret para completar una acción adicional en el navegador.
