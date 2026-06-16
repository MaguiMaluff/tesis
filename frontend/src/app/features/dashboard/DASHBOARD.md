# frontend/src/app/features/dashboard

## Responsabilidad

Agrupa la vista principal de monitoreo y el detalle asociado a perfiles o métricas del sistema.

## Archivos y función

- `dashboard-module.ts`: módulo de carga diferida y rutas de la feature.
- `dashboard.service.ts`: servicio de acceso a datos del dashboard.
- `overview/`: resumen principal de indicadores.
- `detail/`: vista detallada ligada a un perfil o entidad.
- `dashboard.service.spec.ts`: prueba del servicio.

## Relación con el resto del proyecto

Es la primera vista protegida después del login. Consume `ApiService.getDashboardSummary()` y sirve como punto de navegación hacia hijos, conversaciones y casos.