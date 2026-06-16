# frontend/src/app

## Responsabilidad

Contiene el componente raíz, la configuración global de la app y la definición principal de rutas.

## Archivos y función

- `app.ts`: componente raíz que monta la navegación y el shell general.
- `app.html`: plantilla principal.
- `app.css`: estilos del shell.
- `app.config.ts`: proveedores globales, router y cliente HTTP con interceptores.
- `app.routes.ts`: rutas del flujo actual con login, signup y áreas protegidas.
- `app-routing-module.ts`: definición alternativa de rutas basada en `NgModule`.
- `app.spec.ts`: prueba base del componente raíz.
- `core/`: servicios compartidos, guardias e interceptores globales.
- `features/`: áreas funcionales de la aplicación.
- `shared/`: componentes reutilizables de layout.

## Relación con el resto del proyecto

`app/` es el centro de navegación del frontend. Desde aquí se conectan la autenticación, el enrutado diferido y las vistas que consumen la API.