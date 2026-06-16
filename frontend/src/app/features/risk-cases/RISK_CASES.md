# frontend/src/app/features/risk-cases

## Responsabilidad

Centraliza el listado y detalle de casos de riesgo detectados por el sistema.

## Archivos y función

- `risk-cases-module.ts`: módulo de carga diferida y rutas de la feature.
- `risk-case.service.ts`: servicio base de la feature; hoy funciona como punto de extensión para acceso a casos.
- `list/`: listado de casos.
- `detail/`: vista detallada de un caso.

## Relación con el resto del proyecto

Consume `ApiService.getRiskCases()` y `ApiService.getRiskCase()`. La información proviene de la API y, en último término, del worker que crea los casos a partir de los runs procesados.