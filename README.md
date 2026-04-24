# tesis — Instagram Webhook + Preprocess (MVP)

## What this is
- `apps/api`: Flask webhook receiver for Instagram messaging events.
- `apps/worker`: background worker that creates `preprocess_runs` hourly or when a conversation has >= 10 pending messages.
- Uses Supabase Postgres. Does NOT store message text (only hashes/features).

## Setup
1. Create `.env` from `.env.example`
2. Run SQL migration in Supabase: `migrations/001_init.sql`
3. Install deps:
   ```bash
   pip install -r requirements.txt
   ```
4. Run API locally:
   ```bash
   python -m apps.api.app
   ```
5. Run worker locally:
   ```bash
   python -m apps.worker.worker
   ```

## Webhook endpoints
- GET `/webhook` — Meta subscription verification
- POST `/webhook` — receives events

### Signature validation
POST requests must include `X-Hub-Signature-256`. The API validates it using `META_APP_SECRET`.
If invalid, returns 403 and does not store anything.

## Data model (high level)
- conversations: per (ig_user_id, peer_id) state + pending_count
- message_events: per message `mid` unique, no text stored
- preprocess_runs: windows ready for AI, with `fetch_plan` only

## Security notes (MVP)
- Backend uses `SUPABASE_SERVICE_ROLE_KEY` (server-side only).
- Do NOT expose service role key in the frontend.