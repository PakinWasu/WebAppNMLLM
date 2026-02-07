from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGODB_URI: str = "mongodb://mongodb:27017"
    MONGODB_DB_NAME: str = "manage_network_projects"

    # Qwen2.5:7b - โมเดลเฉพาะทางสำหรับงาน technical analysis
    # เร็วกว่า 14b/32b มาก เหมาะกับ CPU-only และลด timeout risk
    # ต้องการ RAM ~4-6GB, Model size ~4.7GB
    AI_MODEL_NAME: str = "qwen2.5:7b"
    AI_MODEL_VERSION: str = "v2-7b"
    # Default: ใช้ Ollama container ใน Docker network
    # สำหรับ Development บน Host: เปลี่ยนเป็น http://host.docker.internal:11434
    AI_MODEL_ENDPOINT: str = "http://ollama:11434"

    JWT_SECRET: str = "change_me"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MIN: int = 60 * 24
    TEMP_PASSWORD_ENCRYPTION_KEY: str = "change_me_temp_pwd_key"  # Should be set in .env for production
    
    # Read from environment variables first (loaded by docker-compose from .env),
    # then from .env file, then use defaults
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()

