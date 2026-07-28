import os


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://taskflow:taskflow@localhost:5432/taskflow",
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "taskflow-secret")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    elasticsearch_url: str = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    elasticsearch_enabled: bool = os.getenv(
        "ELASTICSEARCH_ENABLED", "true"
    ).lower() not in ("false", "0", "")
    cors_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]
    training_defects: str = os.getenv("TRAINING_DEFECTS", "")


settings = Settings()
