from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    control_service_token: str = ""


settings = Settings()
