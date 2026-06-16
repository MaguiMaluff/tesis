# frontend/src/app/core

## Responsabilidad

Agrupa la infraestructura transversal de la app Angular: autenticación, protección de rutas y acceso HTTP compartido.

## Archivos y función

- `guards/`: validación de acceso a rutas protegidas.
- `interceptors/`: modificación global de requests HTTP.
- `services/`: servicios base reutilizados por las features.

## Relación con el resto del proyecto

Todo el frontend depende de este nivel para autenticación y comunicación con la API. Las features no deberían duplicar lógica de token, transporte HTTP ni validación de sesión.