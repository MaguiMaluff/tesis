# frontend/src/app/core/interceptors

## Responsabilidad

Centraliza la modificación de requests HTTP antes de salir del navegador.

## Archivos y función

- `auth.interceptor.ts`: agrega el header `Authorization` con el JWT almacenado en `localStorage`.

## Relación con el resto del proyecto

Permite que las llamadas de `ApiService` lleguen autenticadas a la API sin repetir lógica en cada feature.