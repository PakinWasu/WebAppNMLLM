from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGODB_URI: str = "mongodb://mongodb:27017"
    MONGODB_DB_NAME: str = "manage_network_projects"

    # Qwen2.5-coder:14b - โมเดลเฉพาะทางสำหรับงาน technical analysis
    # สมดุลระหว่างความแม่นยำและประสิทธิภาพ (เร็วกว่า 32b, ใช้ resource น้อยกว่า)
    # ต้องการ RAM ~8-10GB, Model size ~8GB
    AI_MODEL_NAME: str = "qwen2.5-coder:14b"
    AI_MODEL_VERSION: str = "v2-coder-14b"
    # Default: ใช้ Ollama container ใน Docker network
    # สำหรับ Development บน Host: เปลี่ยนเป็น http://host.docker.internal:11434
    AI_MODEL_ENDPOINT: str = "http://ollama:11434"

    JWT_SECRET: str = "change_me"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MIN: int = 60 * 24
    TEMP_PASSWORD_ENCRYPTION_KEY: str = "change_me_temp_pwd_key"  # Should be set in .env for production
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

