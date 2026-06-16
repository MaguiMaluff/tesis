# frontend/src/app/core/services

## Responsabilidad

Contiene servicios compartidos por toda la aplicación.

## Archivos y función

- `api.ts`: cliente tipado para los endpoints del backend y modelos de respuesta usados por las vistas.
- `auth.ts`: manejo de login, sesión, tokens y usuario actual en el navegador.
- `api.spec.ts`: pruebas del cliente API.
- `auth.spec.ts`: pruebas del servicio de autenticación.

## Relación con el resto del proyecto

Las features consumen estos servicios en lugar de hablar con `HttpClient` de forma directa. Así se mantiene un contrato único con la API y un solo lugar para la sesión.