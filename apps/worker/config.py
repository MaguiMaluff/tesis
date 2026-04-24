import os
from dataclasses import dataclass

@dataclass(frozen=True)
class WorkerConfig:
    api_version: str
    access_token: str
    ig_account_id: str

    supabase_url: str
    supabase_service_role_key: str

    threshold_messages: int
    threshold_poll_seconds: int
    hourly_poll_seconds: int

def load_worker_config() -> WorkerConfig:
    api_version = os.getenv("API_VERSION", "v25.0")
    access_token = os.getenv("ACCESS_TOKEN", "")
    ig_account_id = os.getenv("IG_ACCOUNT_ID", "").strip()

    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    threshold_messages = int(os.getenv("WORKER_THRESHOLD_MESSAGES", "10"))
    threshold_poll_seconds = int(os.getenv("WORKER_THRESHOLD_POLL_SECONDS", "120"))
    hourly_poll_seconds = int(os.getenv("WORKER_HOURLY_POLL_SECONDS", "60"))

    missing = []
    for k, v in [
        ("ACCESS_TOKEN", access_token),
        ("IG_ACCOUNT_ID", ig_account_id),
        ("SUPABASE_URL", supabase_url),
        ("SUPABASE_SERVICE_ROLE_KEY", supabase_service_role_key),
    ]:
        if not v:
            missing.append(k)
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    return WorkerConfig(
        api_version=api_version,
        access_token=access_token,
        ig_account_id=ig_account_id,
        supabase_url=supabase_url,
        supabase_service_role_key=supabase_service_role_key,
        threshold_messages=threshold_messages,
        threshold_poll_seconds=threshold_poll_seconds,
        hourly_poll_seconds=hourly_poll_seconds,
    )