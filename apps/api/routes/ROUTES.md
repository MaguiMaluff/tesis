# apps/api/routes

## Responsabilidad

Contiene los blueprints HTTP de la API. Cada archivo agrupa endpoints por dominio funcional.

## Archivos y función

- `auth.py`: login, signup, logout y perfil actual.
- `children.py`: alta, listado y detalle de perfiles administrados.
- `conversations.py`: listado, detalle, eventos y consultas por cuenta.
- `dashboard.py`: resumen agregado para la vista principal.
- `risk_cases.py`: listado, detalle y cierre de casos de riesgo.
- `stats.py`: métricas generales del sistema.
- `__init__.py`: marca el paquete.

## Relación con el resto del proyecto

Las rutas dependen de `auth_middleware.py` para proteger acceso, de `services.py` para serializar respuestas y de `models/` para leer o actualizar el estado persistido.