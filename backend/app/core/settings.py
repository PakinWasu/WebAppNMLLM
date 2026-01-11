from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGODB_URI: str = "mongodb://mongodb:27017"
    MONGODB_DB_NAME: str = "manage_network_projects"

    AI_MODEL_NAME: str = "qwen2.5:7b"
    AI_MODEL_VERSION: str = "v1-desktop"
    AI_MODEL_ENDPOINT: str = "http://host.docker.internal:11434"

    JWT_SECRET: str = "change_me"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MIN: int = 60 * 24
    TEMP_PASSWORD_ENCRYPTION_KEY: str = "change_me_temp_pwd_key"  # Should be set in .env for production
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

