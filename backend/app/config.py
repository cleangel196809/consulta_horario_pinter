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

    test_username: str = "consulta_prueba"
    test_password: str = "prueba123"

    # Notificaciones por correo (opcional). Si smtp_host queda vacío, el envío
    # de notificaciones queda deshabilitado y la API lo indica claramente en
    # vez de fallar.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-responder@pi.edu.co"
    smtp_use_tls: bool = True

    @property
    def smtp_configurado(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
