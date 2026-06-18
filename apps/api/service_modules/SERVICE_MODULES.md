# apps/api/service_modules

## Responsabilidad

Agrupa la lógica interna reutilizable de la API. Estos módulos separan responsabilidades que antes estaban concentradas en `services.py`, manteniendo ese archivo como fachada de compatibilidad para el resto del proyecto.

## Archivos y función

- `utils.py`: helpers generales de fechas, UUIDs y conversiones seguras.
- `risk.py`: normalización de etapas, etiquetas, niveles de riesgo y extracción de señales desde snapshots.
- `privacy.py`: sanitización de salidas de IA para remover datos privados, citas y menciones a información aportada por el menor.
- `auth_tokens.py`: generación de tokens JWT para usuarios autenticados.
- `bundles.py`: armado del bundle de datos asociado a un usuario, incluyendo perfiles, cuentas, conversaciones, eventos, casos y snapshots.
- `serializers.py`: serialización de modelos ORM a payloads JSON consumidos por el frontend.
- `dashboard_service.py`: armado del resumen de dashboard y métricas generales.
- `__init__.py`: marca el paquete para importaciones internas.

## Relación con el resto del proyecto

`services.py` reexporta las funciones principales de esta carpeta para conservar imports existentes. Las rutas de la API consumen esa fachada, mientras que estos módulos mantienen la implementación separada por responsabilidad.
