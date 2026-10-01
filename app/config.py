from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration read from environment variables (case insensitive)."""

    apiversion: str = "2.0"
    data_dir: Path = Path("/data")

    bafu_url_2: str | None = None
    bafu_url_6: str | None = None
    bafu_user: str | None = None
    bafu_pass: str | None = None
    bafu_healthcheck: str | None = None

    @property
    def feeds(self) -> dict[str, str | None]:
        return {"bafu_url_2": self.bafu_url_2, "bafu_url_6": self.bafu_url_6}


settings = Settings()
