import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Config:
    port: int
    verify_token: str
    meta_app_secret: str
    secret_key: str
    jwt_expiration_hours: int
    database_uri: str


def load_config() -> Config:
    port = int(os.getenv("PORT", "3000"))

    verify_token = os.getenv("VERIFY_TOKEN", "")
    meta_app_secret = os.getenv("META_APP_SECRET", "")
    secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
    jwt_expiration_hours = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

    DB_PATH = Path(os.getenv("SQLITE_DATABASE_URL",""))

    database_uri = f"sqlite:///{DB_PATH}"
    return Config(
        port=port,
        verify_token=verify_token,
        meta_app_secret=meta_app_secret,
        secret_key=secret_key,
        jwt_expiration_hours=jwt_expiration_hours,
        database_uri=database_uri,
    )