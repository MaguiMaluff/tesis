import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    port: int
    verify_token: str
    meta_app_secret: str
    ig_account_id: str

    supabase_url: str
    supabase_service_role_key: str

def load_config() -> Config:
    port = int(os.getenv("PORT", "3000"))
    verify_token = os.getenv("VERIFY_TOKEN", "")
    meta_app_secret = os.getenv("META_APP_SECRET", "")
    ig_account_id = os.getenv("IG_ACCOUNT_ID", "").strip()

    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    missing = []
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