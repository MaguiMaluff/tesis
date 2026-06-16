# apps/worker

## Responsabilidad

Contiene el proceso en segundo plano que toma conversaciones pendientes, reconstruye ventanas de mensajes desde Instagram y genera los insumos para el análisis posterior.

## Archivos principales

- `worker.py`: ejecuta los loops de barrido por umbral y por tiempo.
- `jobs.py`: coordina locks, creación de `preprocess_runs` y transición de estado de conversaciones.
- `ai_runner.py`: consume runs listos, arma el prompt y escribe resultados de IA.
- `ai_client.py`: cliente compatible con endpoints de chat completions.
- `ai_prompt.py`: prompt del sistema y construcción del prompt de usuario.
- `build_transcript.py`: exporta ventanas a JSON en `transcripts/`.
- `ig_api.py`: cliente para Graph API de Instagram.
- `resolve_conversation.py`: resuelve `conversation_ext_id` a partir de `peer_id`.
- `config.py`: variables de entorno y parámetros del worker.
- `__init__.py`: marca el paquete.

## Relación con el resto del proyecto

El worker comparte base con la API, lee `conversations` y `preprocess_runs`, y escribe los resultados que luego consume el frontend. También depende de credenciales de Instagram y, si aplica, de credenciales de IA.