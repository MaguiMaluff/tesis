# frontend/src/app/features

## Responsabilidad

Agrupa las áreas funcionales visibles para el usuario final.

## Carpetas principales

- `auth/`: login y registro.
- `children/`: alta de perfiles administrados.
- `conversations/`: listado y detalle de conversaciones.
- `dashboard/`: resumen general y vistas de detalle.
- `risk-cases/`: listado y detalle de casos de riesgo.

## Relación con el resto del proyecto

Cada feature consume `core/services/api.ts` y, cuando corresponde, está protegida por `AuthGuard`. El enrutado se resuelve desde `app.routes.ts`.