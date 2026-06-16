# tesis

Plataforma para monitorear conversaciones de Instagram, registrar eventos mínimos del webhook y preparar ventanas de análisis para un proceso de preprocesamiento y evaluación de riesgo.

## Arquitectura

| Capa | Carpeta | Responsabilidad |
| --- | --- | --- |
| Presentación | `frontend/` | Aplicación Angular para login, tablero, conversaciones y casos de riesgo. |
| API | `apps/api/` | Flask expone autenticación, webhook de Instagram y endpoints de consulta. |
| Procesamiento | `apps/worker/` | Consume pendientes, reconstruye ventanas de mensajes y genera `preprocess_runs` y casos de riesgo. |
| Persistencia | Base relacional configurada por entorno | Guarda usuarios, hijos, cuentas, conversaciones, eventos y casos. |
| Soporte | `scripts/` y `transcripts/` | Utilidades locales y exportes JSON del worker. |

## Flujo general

1. El usuario entra al frontend Angular, inicia sesión y obtiene un token JWT.
2. El frontend llama a la API con ese token para consultar dashboard, conversaciones, hijos y casos de riesgo.
3. Instagram envía eventos al webhook de Flask; la API valida la firma, normaliza el payload y guarda solo metadata mínima.
4. El worker lee los pendientes desde la misma base, crea `preprocess_runs`, resuelve la conversación externa y, si corresponde, prepara el análisis posterior.
5. Los resultados vuelven a la base y el frontend los vuelve a consultar para mostrar el estado actualizado.

## Módulos principales

- `apps/api/`: contratos HTTP, modelos, autenticación y lógica de persistencia.
- `apps/worker/`: orquestación de colas simples, acceso a Instagram y consumo de IA.
- `frontend/`: interfaz de operación y visualización.
- `scripts/`: utilidades de desarrollo local.
- `DB.md`: detalle del modelo de datos y sus relaciones.

## Documentación por carpeta

- `apps/APPS.md`
- `apps/api/API.md`
- `apps/api/models/MODELS.md`
- `apps/api/routes/ROUTES.md`
- `apps/worker/WORKER.md`
- `frontend/FRONTEND.md`
- `frontend/src/SRC.md`
- `frontend/src/environments/ENVIRONMENTS.md`
- `frontend/src/app/APP.md`
- `frontend/src/app/core/CORE.md`
- `frontend/src/app/core/guards/GUARDS.md`
- `frontend/src/app/core/interceptors/INTERCEPTORS.md`
- `frontend/src/app/core/services/SERVICES.md`
- `frontend/src/app/features/FEATURES.md`
- `frontend/src/app/features/auth/AUTH.md`
- `frontend/src/app/features/children/CHILDREN.md`
- `frontend/src/app/features/conversations/CONVERSATIONS.md`
- `frontend/src/app/features/dashboard/DASHBOARD.md`
- `frontend/src/app/features/risk-cases/RISK_CASES.md`
- `frontend/src/app/shared/SHARED.md`
- `frontend/src/app/shared/components/COMPONENTS.md`
- `scripts/SCRIPTS.md`

## Desarrollo local

Dependencias Python:

```bash
pip install -r requirements.txt
```

API local:

```bash
python -m apps.api.app
```

Worker local:

```bash
python -m apps.worker.worker
```

Frontend local:

```bash
cd frontend
npm install
npm start
```

## Notas de persistencia y seguridad

- El backend valida `X-Hub-Signature-256` antes de aceptar eventos del webhook.
- La API y el worker comparten la misma base; el frontend solo consume la API.
- No se expone ningún secreto de servidor al navegador.
- El detalle del esquema está documentado en `DB.md`.
