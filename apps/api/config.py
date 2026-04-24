import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """
    Configuration for the Flask API service.

    NOTE: frozen=True makes it immutable so config can't be modified accidentally at runtime.
    """
    port: int

    # Meta webhook verification (GET /webhook)
    verify_token: str

    # Meta webhook signature validation (POST /webhook)
    meta_app_secret: str

    # Only process webhook entries for this IG account id
    ig_account_id: str

    # Supabase connection (server-side only)
    supabase_url: str
    supabase_service_role_key: str


def load_config() -> Config:
    """
    Load required environment variables and fail fast if any are missing.

    This prevents running the webhook receiver in a partially configured or unsafe state.
    """
    # Flask port (Render usually sets PORT; locally defaults to 3000)
    port = int(os.getenv("PORT", "3000"))

    # Meta / Instagram webhook config
    verify_token = os.getenv("VERIFY_TOKEN", "")
    meta_app_secret = os.getenv("META_APP_SECRET", "")

    # ID of the IG account that should be accepted/processed from payload.entry[].id
    # .strip() helps avoid subtle bugs when copying env vars with whitespace.
    ig_account_id = os.getenv("IG_ACCOUNT_ID", "").strip()

    # Supabase (service role key is powerful; server-side only)
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # Validate required env vars
    missing: list[str] = []
    for k, v in [
        ("VERIFY_TOKEN", verify_token),
        ("META_APP_SECRET", meta_app_secret),
        ("IG_ACCOUNT_ID", ig_account_id),
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
        ig_account_id=ig_account_id,
        supabase_url=supabase_url,
        supabase_service_role_key=supabase_service_role_key,
    )