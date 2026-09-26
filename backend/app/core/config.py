from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "postgresql+psycopg://project_start:project_start@db:5432/project_start"

    max_bot_token: str = ""
    max_init_data_max_age_seconds: int = 24 * 60 * 60
    # Verified against the X-Max-Bot-Api-Secret header on incoming webhook
    # calls (see app/api/bot_webhook.py) — this is the only thing standing
    # between "trust update.user as-is" and an unauthenticated caller.
    max_bot_webhook_secret: str = ""
    max_bot_api_base_url: str = "https://platform-api2.max.ru"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    admin_password: str = "admin"

    auth_rate_limit_per_minute: int = 20
    webhook_rate_limit_per_minute: int = 120
    webhook_dedup_ttl_seconds: int = 10 * 60

    # Demo mode: lets anyone open the web app without MAX via /auth/demo
    # (see app/api/auth.py). On by default so judges can open the public link
    # at a hackathon demo — set DEMO_MODE=false in prod to disable it.
    demo_mode: bool = True
    demo_max_user_id: int = -1
    demo_user_name: str = "Демо-студент"

    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    # Comma-separated origins; pydantic-settings expects JSON for list-typed env
    # vars, which is awkward in a plain .env file, so this stays a plain string.
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def reject_insecure_production_defaults(self) -> "Settings":
        if self.app_env.lower() not in {"production", "prod"}:
            return self

        problems = []
        if self.jwt_secret == "dev-secret-change-me" or len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET must be a random value of at least 32 characters")
        if self.admin_password == "admin" or len(self.admin_password) < 8:
            problems.append("ADMIN_PASSWORD must be at least 8 characters and not the default")
        if problems:
            raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self


settings = Settings()
