# apps/api

## Responsabilidad

Implementa la API Flask del proyecto. Aquí vive la entrada HTTP principal: autenticación, webhook de Instagram, consulta de tableros y acceso a entidades del dominio.

## Archivos principales

- `app.py`: crea la aplicación Flask, registra blueprints, valida el webhook y persiste eventos entrantes.
- `auth_middleware.py`: genera y valida JWT, y protege las rutas privadas.
- `config.py`: carga variables de entorno y arma la configuración de ejecución.
- `database.py`: instancia SQLAlchemy.
- `normalize.py`: adapta payloads de Instagram al formato interno.
- `services.py`: helpers de serialización, armado de bundles y utilidades de dominio.
- `signature.py`: verifica la firma `X-Hub-Signature-256`.
- `models/`: definición de las entidades persistidas.
- `routes/`: blueprints HTTP agrupados por caso de uso.
- `instance/`: almacén local de runtime; en esta instalación contiene la base SQLite generada durante el desarrollo.
- `__init__.py`: marca el paquete.

## Relación con el resto del proyecto

La API es consumida por el frontend Angular y comparte persistencia con el worker. También recibe el webhook de Instagram, que alimenta la tabla de eventos mínimos y actualiza el estado de conversaciones y casos de riesgo.

## Puntos de entrada

- `GET /webhook`: verificación de suscripción.
- `POST /webhook`: recepción de eventos.
- `GET /`: health check básico.