# frontend/src/environments

## Responsabilidad

Define la configuración dependiente del entorno para la app Angular.

## Archivos y función

- `environment.ts`: valores de desarrollo.
- `environment.prod.ts`: valores de producción.

## Relación con el resto del proyecto

Los servicios de Angular leen `environment.apiUrl` para apuntar a la API Flask correcta según el despliegue.