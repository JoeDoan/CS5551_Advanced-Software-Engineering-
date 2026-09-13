import os
from typing import List


class Settings:
    PROJECT_NAME: str = "OptiSched API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./optisched.db")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    @property
    def cors_origins(self) -> List[str]:
        origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        return [o.strip() for o in origins.split(",") if o.strip()]


settings = Settings()
