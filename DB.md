# Base de Datos

Este proyecto usa **SQLite** como base de datos local del backend. En desarrollo, el archivo vive en `apps/api/instance/monitoring.db`.

La base es el estado operativo del sistema: guarda usuarios, perfiles administrados, cuentas de Instagram, conversaciones, eventos mínimos del webhook, runs de preprocesamiento y casos de riesgo.

> El esquema actual está definido en los modelos SQLAlchemy dentro de `apps/api/models/`.

---

## Principios del esquema

- No se guarda el texto completo de los mensajes.
- Solo se persiste metadata, contadores, hashes y resultados derivados.
- La API y el worker comparten la misma base.
- El flujo de relaciones sigue la lógica del producto: usuario -> hijo -> cuenta IG -> conversación -> eventos / preprocess runs / casos.

---

## 1) `users`

Tabla de usuarios que acceden al panel.

### Campos principales

- `id` *(string, PK)*: identificador interno.
- `email` *(string, unique, not null)*: correo de acceso.
- `password_hash` *(string, not null)*: contraseña cifrada.
- `full_name` *(string, not null)*: nombre visible.
- `created_at` *(datetime, not null)*: alta del usuario.

### Relación

- Un usuario puede tener muchos `children`.

---

## 2) `children`

Perfiles administrados desde el dashboard.

### Campos principales

- `id` *(string, PK)*
- `parent_id` *(string, FK -> users.id, not null)*: dueño del perfil.
- `display_name` *(string, not null)*: nombre visible.
- `created_at` *(datetime, not null)*

### Relación

- Un `child` pertenece a un `user`.
- Un `child` puede tener una o más cuentas de Instagram asociadas.

---

## 3) `ig_accounts`

Cuentas de Instagram monitoreadas por el sistema.

### Campos principales

- `id` *(string, PK)*
- `child_id` *(string, FK -> children.id, not null)*: perfil al que pertenece.
- `ig_user_id` *(string, unique, not null)*: ID externo de Instagram.
- `ig_username` *(string, not null)*: usuario visible.
- `access_token` *(string, not null)*: token para consultar la API de Instagram.
- `token_expires_at` *(datetime, null)*: vencimiento del token.
- `webhook_enabled` *(bool, not null, default true)*: habilita recepción de eventos.
- `status` *(string, not null, default 'active')*: estado operativo.
- `created_at` *(datetime, not null)*

### Relación

- Una cuenta IG pertenece a un `child`.
- Una cuenta IG puede tener muchas `conversations`.

---

## 4) `conversations`

Tabla principal de estado por conversación.

### Campos principales

- `id` *(string, PK)*
- `ig_account_id` *(string, FK -> ig_accounts.id, not null)*: cuenta que recibe los mensajes.
- `peer_id` *(string, not null)*: persona/cuenta del otro lado del chat.
- `conversation_ext_id` *(string, unique, null)*: ID externo de la conversación en Instagram.
- `created_at` *(datetime, not null)*
- `last_message_at` *(datetime, null)*: último mensaje observado.
- `last_preprocessed_at` *(datetime, null)*: último run procesado.
- `pending_count` *(int, not null, default 0)*: cantidad de mensajes pendientes.
- `pending_since` *(datetime, null)*: inicio de la ventana pendiente.
- `processing_lock_until` *(datetime, null)*: bloqueo temporal para evitar doble procesamiento.
- `processing_lock_by` *(string, null)*: origen del lock.
- `rolling_summary` *(json, not null, default {})*: resumen acumulado.
- `status` *(string, not null, default 'active')*: `active` o `archived`.

### Relación

- Una conversación pertenece a una cuenta IG.
- Una conversación puede tener muchos `message_events`.
- Una conversación puede tener muchos `preprocess_runs`.
- Una conversación puede tener muchos `risk_cases`.

---

## 5) `message_events`

Registro mínimo de mensajes recibidos por webhook.

### Campos principales

- `id` *(string, PK)*
- `conversation_id` *(string, FK -> conversations.id, not null)*
- `mid` *(string, unique, not null)*: ID del mensaje en Instagram.
- `sent_at` *(datetime, not null)*: timestamp del evento.
- `direction` *(string, not null)*: `inbound` o `outbound`.
- `text_hash` *(string, null)*: hash del contenido.
- `features` *(json, not null, default {})*: features derivadas sin texto.
- `created_at` *(datetime, not null)*

### Relación

- Cada evento pertenece a una conversación.
- Se usa para deduplicación, auditoría ligera y consulta temporal.

---

## 6) `preprocess_runs`

Ventanas preparadas para reconstrucción y análisis posterior.

### Campos principales

- `id` *(string, PK)*
- `conversation_id` *(string, FK -> conversations.id, not null)*
- `window_start` *(datetime, not null)*
- `window_end` *(datetime, not null)*
- `trigger` *(string, not null)*: origen del run, normalmente `hourly` o `threshold_10`.
- `status` *(string, not null, default 'queued')*: estado operativo del run.
- `message_count` *(int, not null, default 0)*
- `fetch_plan` *(json, not null, default {})*: receta para reconstruir el transcript desde Instagram.
- `error` *(text, null)*
- `created_at` *(datetime, not null)*
- `updated_at` *(datetime, not null)*

### Relación

- Cada run pertenece a una conversación.
- El worker crea estos registros antes de reconstruir mensajes o enviar análisis a IA.

---

## 7) `risk_cases`

Casos de riesgo derivados del análisis de una conversación.

### Campos principales

- `id` *(string, PK)*
- `conversation_id` *(string, FK -> conversations.id, not null)*
- `opened_at` *(datetime, not null)*
- `status` *(string, not null, default 'open')*: `open` o `closed`.
- `stage` *(int, not null, default 0)*: etapa de riesgo.
- `confidence` *(float, not null, default 0.0)*: confianza estimada.
- `reason_safe` *(text, null)*: explicación resumida sin datos sensibles.
- `evidence_window_start` *(datetime, null)*
- `evidence_window_end` *(datetime, null)*

### Relación

- Cada caso pertenece a una conversación.
- Un caso puede tener muchas `case_snapshots`.

---

## 8) `case_snapshots`

Snapshots del análisis asociado a un caso de riesgo.

### Campos principales

- `id` *(string, PK)*
- `risk_case_id` *(string, FK -> risk_cases.id, not null)*
- `snapshot_json` *(json, not null, default {})*: salida completa del análisis.
- `encrypted` *(bool, not null, default false)*: indica si el contenido fue cifrado.
- `created_at` *(datetime, not null)*

### Relación

- Cada snapshot pertenece a un caso de riesgo.

---

## Resumen de relaciones

- `users` -> `children`
- `children` -> `ig_accounts`
- `ig_accounts` -> `conversations`
- `conversations` -> `message_events`
- `conversations` -> `preprocess_runs`
- `conversations` -> `risk_cases`
- `risk_cases` -> `case_snapshots`

---

## Seguridad y privacidad

1. No se guarda el texto completo de los mensajes.
2. Los tokens de Instagram viven solo en backend.
3. El frontend solo consume la API; nunca accede directo a la base.
4. El worker usa la misma base para completar el pipeline de preprocesamiento y análisis.

---

## Notas operativas

- En desarrollo, SQLite se inicializa automáticamente con el arranque de la API.
- La base puede regenerarse si se borra `apps/api/instance/monitoring.db`.
