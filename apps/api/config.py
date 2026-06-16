import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """
    Configuration for the Flask API service.
    """
    port: int

    # Meta webhook verification (GET /webhook)
    verify_token: str

    # Meta webhook signature validation (POST /webhook)
    meta_app_secret: str

    # Supabase connection (server-side only)
    supabase_url: str
    supabase_service_role_key: str


def load_config() -> Config:
    port = int(os.getenv("PORT", "3000"))

    verify_token = os.getenv("VERIFY_TOKEN", "")
    meta_app_secret = os.getenv("META_APP_SECRET", "")

    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    missing: list[str] = []
    for k, v in [
        ("VERIFY_TOKEN", verify_token),
        ("META_APP_SECRET", meta_app_secret),
        ("SUPABASE_URL", supabase_url),
        ("SUPABASE_SERVICE_ROLE_KEY", supabase_service_role_key),
    ]:
        if not v:
            missing.append(k)

    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    return Config(
        port=port,
        verify_token=verify_token,
        meta_app_secret=meta_app_secret,
        supabase_url=supabase_url,
        supabase_service_role_key=supabase_service_role_key,
    )