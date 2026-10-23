from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://root:admin@localhost:3306/blog"
    secret_key: str = "dev-only-change-this-secret-key-before-deployment"
    access_token_expire_minutes: int = 60
    upload_dir: str = "uploads"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
