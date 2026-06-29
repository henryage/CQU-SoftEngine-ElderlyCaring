"""应用配置 - 基于 pydantic-settings，从 .env 读取。"""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用
    app_name: str = "模糊视觉辅助问答系统后端"
    app_env: str = "dev"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_prefix: str = "/api/v1"

    # 开发模式
    dev_mode: bool = True
    mock_openid_eldery: str = "dev_elder_001"
    mock_openid_child: str = "dev_child_001"

    # 微信
    wx_app_id: str = ""
    wx_app_secret: str = ""

    # JWT
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    # MySQL
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "ftraining_db"
    mysql_pool_size: int = 10
    mysql_max_overflow: int = 20

    # Chroma
    chroma_persist_path: str = "./data/chroma"
    chroma_collection_memory: str = "long_term_memory"

    # 上传
    upload_dir: str = "./data/uploads"
    upload_url_prefix: str = "/files"

    # LLM
    llm_api_base: str = "https://api.example.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout: int = 60

    # 审计
    audit_retain_days: int = 180

    # CORS
    cors_origins: str = "*"

    @property
    def mysql_dsn(self) -> str:
        """异步 MySQL DSN（aiomysql 驱动，纯 Python 无需编译）。"""
        pwd = f":{self.mysql_password}" if self.mysql_password else ""
        return (
            f"mysql+aiomysql://{self.mysql_user}{pwd}@"
            f"{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def is_dev(self) -> bool:
        return self.app_env == "dev" or self.dev_mode


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
