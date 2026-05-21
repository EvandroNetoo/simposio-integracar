from pathlib import Path

from pydantic_settings import BaseSettings


class EnvSettings(BaseSettings):
    class ConfigDict:
        env_file = str(Path(__file__).parent.parent.parent / '.env')
        env_file_encoding = 'utf-8'
        case_sensitive = True

    # Core Settings
    SECRET_KEY: str = 'change-me-in-production'  # noqa: S105
    DEBUG: bool = True
    ALLOWED_HOSTS: list[str] = ['*']
    CSRF_TRUSTED_ORIGINS: list[str] = []

    # Database
    DATABASE_URL: str = 'sqlite:///db.sqlite3'


env_settings = EnvSettings()
