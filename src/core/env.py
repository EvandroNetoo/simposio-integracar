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

    # Email
    EMAIL_HOST: str = 'localhost'
    EMAIL_PORT: int = 25
    EMAIL_HOST_USER: str = ''
    EMAIL_HOST_PASSWORD: str = ''
    EMAIL_USE_TLS: bool = False
    EMAIL_USE_SSL: bool = False
    DEFAULT_FROM_EMAIL: str = 'noreply@localhost'


env_settings = EnvSettings()
