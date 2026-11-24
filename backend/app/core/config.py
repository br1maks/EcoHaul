from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "EcoHaul API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Сервис вывоза мусора в Минске через Telegram Mini App"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    DOCS_ENABLED: bool = False
    ENABLE_DEV_AUTH: bool = False
    TELEGRAM_ENABLED: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/ecohaul"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_USE_NULL_POOL: bool = False

    SECRET_KEY: str = "changeme-generate-with-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "ecohaul"
    JWT_AUDIENCE: str = "ecohaul-api"
    WS_AUTH_CHECK_SECONDS: float = Field(10, gt=0, le=60)
    TELEGRAM_AUTH_MAX_AGE_SECONDS: int = Field(300, ge=1, le=86400)

    BOT_TOKEN: str = "placeholder_bot_token"
    WEBAPP_URL: str = "https://placeholder.com"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "your-email@gmail.com"
    SMTP_PASSWORD: str = "your-app-password"
    SMTP_FROM_EMAIL: str = "noreply@ecohaul.by"
    SMTP_USE_TLS: bool = True

    PAYMENT_PROVIDER: str = "yookassa"
    PAYMENTS_ENABLED: bool = False
    PAYMENT_CURRENCY: str = Field("BYN", pattern=r"^[A-Z]{3}$")

    YOOKASSA_SHOP_ID: str = "placeholder_shop_id"
    YOOKASSA_SECRET_KEY: str = "placeholder_secret_key"
    YOOKASSA_RETURN_URL: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"

    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

    PHASE_1_LAT_MIN: float = 53.895
    PHASE_1_LAT_MAX: float = 53.906
    PHASE_1_LON_MIN: float = 27.550
    PHASE_1_LON_MAX: float = 27.566

    PHASE_2_LAT_MIN: float = 53.835
    PHASE_2_LAT_MAX: float = 53.965
    PHASE_2_LON_MIN: float = 27.425
    PHASE_2_LON_MAX: float = 27.690

    ALLOWED_STREETS_PHASE_1: List[str] = [
        "аэродромная",
        "белградская",
        "братская",
        "брилевская",
        "германовская",
        "жореса алфёрова",
        "игоря лученка",
        "лейтенанта кижеватова",
        "леонида левина",
        "леонида щемелёва",
        "михаила савицкого",
        "николы теслы",
        "переулок физкультурный",
        "проспект мира",
        "южная магистраль",
    ]

    ALLOWED_STREETS_PHASE_2: List[str] = []

    CURRENT_PHASE: int = 1

    BASE_PRICE_PER_BAG: float = 2.0

    BASIC_SUBSCRIPTION_DISCOUNT: float = 0.2
    PREMIUM_SUBSCRIPTION_DISCOUNT: float = 0.3

    ORDER_OFFER_EXPIRY_SECONDS: int = 60
    MAX_COURIER_DISTANCE_KM: float = 10.0

    MAX_NOTIFICATION_RETRIES: int = 3
    NOTIFICATION_RETRY_DELAY_SECONDS: int = 60

    @property
    def yookassa_return_url_computed(self) -> str:
        if self.YOOKASSA_RETURN_URL:
            return self.YOOKASSA_RETURN_URL
        return f"{self.WEBAPP_URL}/payment/success"

    @property
    def current_phase_bounds(self) -> dict:
        if self.CURRENT_PHASE == 1:
            return {
                "lat_min": self.PHASE_1_LAT_MIN,
                "lat_max": self.PHASE_1_LAT_MAX,
                "lon_min": self.PHASE_1_LON_MIN,
                "lon_max": self.PHASE_1_LON_MAX,
            }
        return {
            "lat_min": self.PHASE_2_LAT_MIN,
            "lat_max": self.PHASE_2_LAT_MAX,
            "lon_min": self.PHASE_2_LON_MIN,
            "lon_max": self.PHASE_2_LON_MAX,
        }

    @property
    def current_phase_streets(self) -> List[str]:
        if self.CURRENT_PHASE == 1:
            return self.ALLOWED_STREETS_PHASE_1
        return self.ALLOWED_STREETS_PHASE_2

settings = Settings()
