import os
from typing import List


class Settings:
    PROJECT_NAME: str = "UMKC Scheduler API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./optisched_foia.db")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    AUTO_SEED: bool = os.getenv("AUTO_SEED", "true").lower() in ("1", "true", "yes")
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", "umkc-optisched-secret-key-2026-cs5551"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")
    )

    @property
    def data_profile(self) -> str:
        return os.getenv("DATA_PROFILE", "uiuc_foia")

    @property
    def DATA_PROFILE(self) -> str:
        return self.data_profile

    @property
    def require_auth(self) -> bool:
        return os.getenv("REQUIRE_AUTH", "true").lower() in ("1", "true", "yes")

    @property
    def cors_origins(self) -> List[str]:
        origins = os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        )
        return [o.strip() for o in origins.split(",") if o.strip()]


settings = Settings()
