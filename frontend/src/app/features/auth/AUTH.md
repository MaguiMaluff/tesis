# frontend/src/app/features/auth

## Responsabilidad

Contiene el flujo de acceso al sistema.

## Archivos y función

- `login/`: formulario de inicio de sesión.
- `signup/`: formulario de registro.

## Relación con el resto del proyecto

Estas vistas interactúan con `AuthService` y son la puerta de entrada al resto de la app. Después del login, el usuario puede acceder a las rutas protegidas.