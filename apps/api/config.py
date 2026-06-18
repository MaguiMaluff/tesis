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


def _database_uri() -> str:
    database_uri = os.getenv("DATABASE_URL", "").strip()
    if database_uri:
        return database_uri

    sqlite_database = os.getenv("SQLITE_DATABASE_URL", "").strip()
    if sqlite_database.startswith("sqlite:"):
        return sqlite_database

    db_path = (
        Path(sqlite_database)
        if sqlite_database
        else Path(__file__).resolve().parent / "instance" / "monitoring.db"
    )
    return f"sqlite:///{db_path}"


def load_config() -> Config:
    return Config(
        port=int(os.getenv("PORT", "3000")),
        verify_token=os.getenv("VERIFY_TOKEN", ""),
        meta_app_secret=os.getenv("META_APP_SECRET", ""),
        secret_key=os.getenv("SECRET_KEY", "dev-secret-key"),
        jwt_expiration_hours=int(os.getenv("JWT_EXPIRATION_HOURS", "24")),
        database_uri=_database_uri(),
    )
