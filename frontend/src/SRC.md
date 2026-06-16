# frontend/src

## Responsabilidad

Contiene el punto de arranque y el código fuente de la aplicación Angular.

## Archivos y función

- `main.ts`: bootstrap de Angular.
- `index.html`: host HTML de la aplicación.
- `styles.css`: estilos globales.
- `app/`: componentes, rutas, servicios y features de la aplicación.
- `environments/`: configuración por entorno.

## Relación con el resto del proyecto

`src/` conecta la configuración de build con la aplicación real. Todo lo que ve el usuario vive dentro de `app/`, y la URL base de la API se toma desde `environments/`.