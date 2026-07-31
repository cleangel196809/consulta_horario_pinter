from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_user: str = "pinter_admin"
    postgres_password: str = "pinter_pass"
    postgres_db: str = "consulta_horario_pinter"
    postgres_host: str = "db"
    postgres_port: int = 5432

    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    admin_username: str = "admin"
    admin_password: str = "admin123"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
