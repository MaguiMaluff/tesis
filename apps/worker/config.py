import os
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkerConfig:
    """
    Configuration for the background worker.
    """
    api_version: str

    # Optional fallback token (use only if ig_accounts.access_token is null)
    access_token_fallback: str

    supabase_url: str
    supabase_service_role_key: str

    threshold_messages: int
    threshold_poll_seconds: int
    hourly_poll_seconds: int


def load_worker_config() -> WorkerConfig:
    api_version = os.getenv("API_VERSION", "v25.0")

    # Optional fallback for dev
    access_token_fallback = os.getenv("ACCESS_TOKEN", "")

    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    threshold_messages = int(os.getenv("WORKER_THRESHOLD_MESSAGES", "10"))
    threshold_poll_seconds = int(os.getenv("WORKER_THRESHOLD_POLL_SECONDS", "120"))
    hourly_poll_seconds = int(os.getenv("WORKER_HOURLY_POLL_SECONDS", "60"))

    missing = []
    for k, v in [
        ("SUPABASE_URL", supabase_url),
        ("SUPABASE_SERVICE_ROLE_KEY", supabase_service_role_key),
    ]:
        if not v:
            missing.append(k)

    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    return WorkerConfig(
        api_version=api_version,
        access_token_fallback=access_token_fallback,
        supabase_url=supabase_url,
        supabase_service_role_key=supabase_service_role_key,
        threshold_messages=threshold_messages,
        threshold_poll_seconds=threshold_poll_seconds,
        hourly_poll_seconds=hourly_poll_seconds,
    )