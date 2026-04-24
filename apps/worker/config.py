import os
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkerConfig:
    """
    Configuration for the background worker.

    The worker needs:
      - Supabase access (service role) to read/write conversation state and preprocess_runs
      - Instagram Graph API access (access token) to resolve conversation_ext_id and fetch messages
      - Polling parameters for threshold/hourly loops
    """
    # Instagram Graph API
    api_version: str
    access_token: str
    ig_account_id: str

    # Supabase
    supabase_url: str
    supabase_service_role_key: str

    # Trigger settings
    threshold_messages: int
    threshold_poll_seconds: int
    hourly_poll_seconds: int


def load_worker_config() -> WorkerConfig:
    """
    Load worker env vars and fail fast if required values are missing.

    Defaults:
      - API_VERSION defaults to v25.0
      - Threshold defaults to 10 messages
      - Polling defaults: threshold 120s, hourly tick 60s
    """
    # Graph API version (safe default)
    api_version = os.getenv("API_VERSION", "v25.0")

    # Graph API access token (required)
    access_token = os.getenv("ACCESS_TOKEN", "")

    # Our IG account id (required)
    ig_account_id = os.getenv("IG_ACCOUNT_ID", "").strip()

    # Supabase (required; service role is server-side only)
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # Worker behavior knobs
    threshold_messages = int(os.getenv("WORKER_THRESHOLD_MESSAGES", "10"))
    threshold_poll_seconds = int(os.getenv("WORKER_THRESHOLD_POLL_SECONDS", "120"))
    hourly_poll_seconds = int(os.getenv("WORKER_HOURLY_POLL_SECONDS", "60"))

    # Validate required env vars
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