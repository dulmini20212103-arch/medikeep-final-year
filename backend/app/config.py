#Pydantic class designed specifically for configuration management.
#automatically reads values from Environment variables
from pydantic_settings import BaseSettings
from typing import Optional

#all configuration values needed
class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

   #Tells Pydantic to load variables from a .env file 
    class Config:
        env_file = ".env"

settings = Settings()


#This configuration module uses Pydantic Settings to securely load and validate environment-based application configuration, ensuring secrets are not hardcoded and misconfiguration is detected at startup