from pydantic_settings import BaseSettings, SettingsConfigDict

from app.version import VERSION


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    offline_mode: bool = False
    geocoder: str = "geoplateforme"  # "geoplateforme" | "nominatim" | "mock"
    geopf_base_url: str = "https://data.geopf.fr/geocodage"
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    overpass_base_url: str = "https://overpass-api.de/api/interpreter"
    nominatim_user_agent: str = f"GeoScopeAnalyst/{VERSION} contact@example.com"
    default_radius_m: int = 1500
    request_timeout_seconds: int = 20
    map_tile_url: str = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    rate_limit_per_second: float = 40.0
    cache_ttl_seconds: int = 86400


settings = Settings()
