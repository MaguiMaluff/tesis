# Tablas de la Base de Datos (Supabase Postgres)

Este proyecto usa Supabase (Postgres) como **storage de estado** y **orquestación**.  
**No se almacena el texto completo de los mensajes** en la base de datos: solo metadata, contadores y planes de reconstrucción (“fetch plans”) para consultar el transcript directamente desde la API de Instagram cuando sea necesario.

> Fuente del esquema: `migration/001_init.sql`

---

## 1) `public.conversations`

Tabla de **estado por conversación**.  
Hay **una fila por (ig_user_id, peer_id)**.

### Columnas

- **id** *(uuid, PK)*  
  ID interno de la DB. Se usa como FK en `message_events` y `preprocess_runs`.

- **ig_user_id** *(text, not null)*  
  ID de la cuenta de Instagram que **recibe** los mensajes.

- **peer_id** *(text, not null)*  
  ID de la cuenta/persona del otro lado del chat.

- **conversation_ext_id** *(text, null)*  
  ID de la **Conversations API** de Instagram (`aWdf...`).  
  No viene en el webhook, se resuelve luego con IG API (ver worker).  
  Es indispensable para hacer `/{conversation_ext_id}/messages` y reconstruir el transcript.

- **created_at** *(timestamptz, not null, default now())*  
  Cuándo se creó la conversación en DB.

- **last_message_at** *(timestamptz, null)*  
  Timestamp del último mensaje observado por el webhook (útil para ordenar, monitorear y debug).

- **last_preprocessed_at** *(timestamptz, null)*  
  Timestamp del último “preprocess” (última vez que se generó un `preprocess_run` para esa conversación).

- **pending_count** *(int, not null, default 0)*  
  Cantidad de mensajes “pendientes” desde el último preprocess.  
  Se incrementa al llegar eventos del webhook y se resetea a 0 cuando el worker crea un `preprocess_run`.

- **pending_since** *(timestamptz, null)*  
  Marca el timestamp del **primer mensaje pendiente**.  
  Define el inicio de la ventana (`window_start`) cuando se dispara un `preprocess_run`.

- **rolling_summary** *(text, null)*  
  Placeholder para futuro (ej. resumen incremental).

- **status** *(text, not null, default 'active')*  
  Estado de la conversación. Actualmente se usa:
  - `active`: el worker la procesa.
  - `archived`: el worker la ignora.

### Constraints / reglas de integridad

- **`conversations_uniq`**: `unique (ig_user_id, peer_id)`  
  Garantiza 1 conversación por par (tu cuenta, peer).

- **`conversations_status_chk`**: `status in ('active','archived')`

### Índices (performance)

- **`conversations_pending_idx`** `(pending_count, pending_since)`  
  Acelera búsquedas de conversaciones pendientes (threshold/hourly).

- **`conversations_last_message_idx`** `(last_message_at desc)`  
  Acelera orden por última actividad.

---

## 2) `public.message_events`

Tabla de **eventos por mensaje** (auditoría mínima).  
Importante: **NO guarda texto**.

### Columnas

- **id** *(uuid, PK)*  
  ID interno del evento.

- **conversation_id** *(uuid, FK → conversations.id, not null)*  
  Referencia a la conversación.  
  `on delete cascade`: si se borra la conversación, se borran sus eventos.

- **mid** *(text, not null)*  
  Message ID de Instagram.  
  Se usa para deduplicación de eventos (reintentos/reenvíos del webhook).

- **sent_at** *(timestamptz, not null)*  
  Timestamp del mensaje (según el evento normalizado).

- **direction** *(text, not null)*  
  Dirección del mensaje:
  - `inbound`: entra a tu cuenta
  - `outbound`: sale desde tu cuenta

- **text_hash** *(text, null)*  
  Hash del contenido. Sirve para features/controles sin guardar el texto original.

- **features** *(jsonb, null)*  
  Features derivadas (ej. flags de riesgo o marcadores simples) **sin texto**.

- **created_at** *(timestamptz, not null, default now())*  
  Cuándo se insertó el evento en DB.

### Constraints / reglas de integridad

- **`message_events_mid_uniq`**: `unique (mid)`  
  Dedupe por message id.

- **`message_events_direction_chk`**: `direction in ('inbound','outbound')`

### Índices

- **`message_events_conv_sent_idx`** `(conversation_id, sent_at desc)`  
  Acelera consultas por conversación y tiempo.

---

## 3) `public.preprocess_runs`

Tabla de **runs de preprocesamiento** (ventanas listas para análisis).  
Guarda un “plan” para reconstruir transcript desde IG API, sin almacenar el transcript.

### Columnas

- **id** *(uuid, PK)*  
  ID del run.

- **conversation_id** *(uuid, FK → conversations.id, not null)*  
  Conversación asociada.

- **window_start** *(timestamptz, not null)*  
  Inicio de la ventana a reconstruir (normalmente `conversations.pending_since`).

- **window_end** *(timestamptz, not null)*  
  Fin de la ventana (momento en el que se creó el run).

- **trigger** *(text, not null)*  
  Motivo del run:
  - `threshold_10`: cuando `pending_count >= 10`
  - `hourly`: barrido por tiempo (si hay pendientes)

- **status** *(text, not null, default 'ready_for_ai')*  
  Estado del run:
  - `ready_for_ai`: listo para que una etapa posterior reconstruya transcript y analice (IA)
  - `skipped`: se decidió no procesar (ej. faltaba `conversation_ext_id`)
  - `error`: falló algo (y queda trazabilidad)

- **message_count** *(int, not null, default 0)*  
  Cantidad de mensajes pendientes al momento del run (informativo / validación).

- **fetch_plan** *(jsonb, not null, default '{}')*  
  “Receta” de reconstrucción. Ejemplo de campos típicos:
  - `source`: "instagram"
  - `api_host`: "graph.instagram.com"  - `api_version`: "env:API_VERSION"
  - `ig_user_id`: tu cuenta
  - `conversation_ext_id`: `aWdf...`
  - `window_start`, `window_end`
  - `fields`: "id,from,to,message,created_time"
  - `strategy`: "fetch_by_conversation_then_filter_by_time"

- **created_at** *(timestamptz, not null, default now())*  
  Cuándo se creó el run.

- **error** *(text, null)*  
  Mensaje de error o razón de “skipped”.

### Constraints / reglas de integridad

- **`preprocess_trigger_chk`**: `trigger in ('hourly','threshold_10')`
- **`preprocess_status_chk`**: `status in ('ready_for_ai','skipped','error')`

### Índices

- **`preprocess_runs_created_idx`** `(created_at desc)`  
  Acelera “últimos runs”.

---

## 4) Tablas “future” (no críticas para el MVP actual)

Estas tablas están definidas en el schema como placeholders para la etapa de IA.  
Actualmente pueden no estar en uso.

### `public.risk_cases`

- **conversation_id** *(uuid FK)*: conversación que originó el caso
- **opened_at**: cuándo se abrió el caso
- **status**: `open` / `closed`
- **stage**: etapa (ej. 0–4) si aplica
- **confidence**: confianza del modelo
- **reason_safe**: razón resumida (sin información sensible)
- **evidence_window_start/end**: ventana que motivó la detección

Constraint: `risk_cases_status_chk` (`open|closed`).

### `public.case_snapshots`

- **risk_case_id** *(uuid FK)*: referencia al caso
- **snapshot_json** *(jsonb)*: output completo de IA / análisis
- **encrypted** *(boolean)*: flag si se cifró
- **created_at**: timestamp

---

# Relaciones entre tablas (resumen)

- `conversations` es la tabla principal (estado por chat).
- `message_events` guarda eventos mínimos por mensaje (sin texto) y referencia a `conversations`.
- `preprocess_runs` guarda ventanas listas para análisis, referenciando a `conversations`.
- `risk_cases` / `case_snapshots` son para análisis futuro (IA).

---

# Notas de seguridad y privacidad

## 1) Principio clave: minimización de datos
- En DB **no se guarda** el texto del mensaje.
- En su lugar se guarda:
  - `mid`, timestamps, direction (auditoría)
  - contadores/estado (`pending_count`, `pending_since`)
  - y `fetch_plan` (para reconstrucción temporal desde IG API)

## 2) Acceso a Supabase
- El backend usa `SUPABASE_SERVICE_ROLE_KEY` (server-side only).
- **Nunca** exponer esa key en frontend o clientes.


## 3) Webhook autenticado
- El endpoint `POST /webhook` valida `X-Hub-Signature-256` con `META_APP_SECRET`.
- Si la firma falla, el request se rechaza y no se inserta nada en DB.

## 4) Tokens de Instagram / Meta
- `ACCESS_TOKEN` debe mantenerse como secreto (env var).
- Si expira o cambia, la reconstrucción de transcript fallará (porque depende de IG API).

---
