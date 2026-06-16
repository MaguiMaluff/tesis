# apps/api/models

## Responsabilidad

Define las entidades ORM que representan el estado operativo del sistema. Estas clases son la base del esquema relacional descrito en `DB.md`.

## Archivos y función

- `user.py`: usuarios que acceden al panel.
- `child.py`: perfiles administrados desde el dashboard.
- `ig_account.py`: cuentas de Instagram asociadas a cada hijo/perfil.
- `conversation.py`: estado por conversación, contadores y metadatos de seguimiento.
- `message_event.py`: registro mínimo de cada mensaje recibido, sin almacenar el texto completo.
- `preprocess_run.py`: ventanas listas para preprocesamiento y su estado de ejecución.
- `risk_case.py`: casos de riesgo detectados o abiertos para seguimiento.
- `case_snapshot.py`: snapshots del análisis asociado a un caso de riesgo.
- `__init__.py`: exporta los modelos para importaciones compactas.

## Relación con el resto del proyecto

Los modelos son usados por la API para persistir y serializar datos, y por el worker para leer pendientes, crear runs y registrar resultados de análisis.