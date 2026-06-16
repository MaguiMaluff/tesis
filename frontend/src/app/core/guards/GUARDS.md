# frontend/src/app/core/guards

## Responsabilidad

Define guardias de navegación que protegen rutas privadas.

## Archivos y función

- `auth-guard.ts`: evita el acceso a áreas protegidas si no existe sesión activa.

## Relación con el resto del proyecto

Usa `AuthService` para decidir si el usuario puede entrar a dashboard, conversaciones y casos de riesgo.