# frontend

## Responsabilidad

Aplicación Angular que ofrece la interfaz de operación del sistema: autenticación, tablero, listado de conversaciones, perfiles administrados y casos de riesgo.

## Archivos principales

- `angular.json`: configuración de Angular CLI.
- `package.json`: dependencias y scripts de desarrollo.
- `tsconfig*.json`: configuración TypeScript.
- `public/`: activos estáticos entregados tal cual al navegador.
- `src/`: código fuente de la aplicación.

## Relación con el resto del proyecto

El frontend no accede a la base directamente. Consume la API Flask, envía el JWT en cada request y renderiza el estado persistido por backend y worker.

## Comandos útiles

```bash
cd frontend
npm install
npm start
npm run build
npm test
```