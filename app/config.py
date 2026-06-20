from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    emr_base_url: str = "https://basata-interview-sandbox-emr.ngrok.app"
    http_timeout_seconds: float = 10.0
    vapi_webhook_secret: str = ""
    enable_idempotency_memory: bool = True
    idempotency_ttl_seconds: int = 900
