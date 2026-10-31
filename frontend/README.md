# Canasta Express — Frontend

Frontend desarrollado con Vue 3 y Vite para los requisitos RF-0001, RF-0002 y RF-0003.

## Requisitos

- Node.js 20 o superior.
- Backend FastAPI ejecutándose en `http://127.0.0.1:8000`.
- Para habilitar Google Identity Services, un ID de cliente OAuth 2.0 configurado también en el backend.

## Ejecución local

Desde este directorio:

```bash
npm install
cp .env.example .env
npm run dev
```

Vite publica la aplicación en `http://localhost:5173` y reenvía las peticiones que comienzan por `/backend` al backend FastAPI. Si el backend usa otro host o puerto, configura `VITE_BACKEND_TARGET` en el entorno donde se inicia Vite.

Para habilitar el botón de Google, configura `VITE_GOOGLE_CLIENT_ID` en el archivo `.env` con el mismo Client ID que utiliza el backend (`GOOGLE_CLIENT_ID`). El backend valida el ID token recibido; el frontend no debe contener secretos OAuth.

Para generar la versión de producción:

```bash
npm run build
npm run preview
```

En producción, configura `VITE_API_BASE_URL` con la URL pública del backend y habilita CORS en FastAPI para el dominio del frontend. La configuración de proxy de Vite solo aplica al servidor de desarrollo.

## Requisitos implementados

- **RF-0001:** registro con los campos de nombre y apellidos que recibe el backend, correo y contraseña. El rol no se envía desde el navegador: el backend asigna el rol `customer`. Los campos de segundo nombre y segundo apellido son opcionales.
- **RF-0002:** autenticación mediante correo y contraseña usando el formulario OAuth2 `application/x-www-form-urlencoded`. También se integra el inicio de sesión con Google mediante Google Identity Services y el endpoint del backend. El JWT se mantiene en memoria, salvo que el usuario active «Recordar sesión».
- **RF-0003:** pantalla de recuperación con correo y código de seis dígitos en el mismo formulario, verificación y pantalla separada para establecer y confirmar la nueva contraseña.

## Contratos de backend utilizados

| Acción | Método y ruta |
| --- | --- |
| Registro | `POST /register/user/` |
| Inicio de sesión | `POST /users/v1/auth/token` |
| Inicio de sesión con Google | `POST /users/v1/auth/google` |
| Solicitar código | `POST /users/v1/auth/password/restore-code` |
| Verificar código | `POST /users/v1/auth/password/verify` |
| Restablecer contraseña | `POST /users/v1/auth/password/reset` |

El formulario de registro envía `contact_info.email`; no envía `user_role` ni otros campos no permitidos. La recuperación conserva el código de seis dígitos que valida el backend.

## Alcance

Esta entrega implementa únicamente RF-0001 a RF-0003. El resto de módulos (catálogo, carrito, checkout y pedidos) queda fuera de este incremento.
