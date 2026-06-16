# apps

## Responsabilidad

Esta carpeta agrupa los dos procesos de backend del sistema: la API HTTP de Flask y el worker de procesamiento en segundo plano.

## Contenido

- `api/`: recibe webhooks, expone endpoints y mantiene el estado operativo.
- `worker/`: revisa conversaciones pendientes, construye ventanas de análisis y dispara el procesamiento posterior.
- `__init__.py`: marca el paquete para importaciones internas.

## Relación con el resto del proyecto

`apps/` es el puente entre el frontend y la persistencia. La API atiende al navegador y al webhook de Instagram; el worker reutiliza el mismo modelo de datos para completar el flujo asíncrono.