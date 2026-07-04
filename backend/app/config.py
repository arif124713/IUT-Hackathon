from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

# .env lives one level above the backend/ package
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    # Database
    database_url: str = "mysql+aiomysql://root:123456@localhost:3306/officepulse"

    # Office schedule
    tz: str = "Asia/Dhaka"
    office_open: str = "09:00"
    office_close: str = "17:00"

    # Simulator
    sim_tick_seconds: int = 5
    sim_time_scale: float = 1.0

    # Demo mode
    demo_mode: bool = False

    # Service URLs
    backend_url: str = "http://localhost:8000"
    mcp_server_url: str = "http://localhost:8001"

    # Backend server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Alerts engine
    alerts_eval_seconds: int = 30
    marathon_minutes: int = 120

    # Device config
    fans_per_room: int = 2
    lights_per_room: int = 3

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
