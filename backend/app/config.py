from functools import lru_cache
import os

from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv("backend/.env")


class Settings(BaseModel):
    serpapi_key: str


@lru_cache
def get_settings() -> Settings:
    key = os.getenv("SERPAPI_KEY")

    if not key:
        raise RuntimeError(
            "SERPAPI_KEY is not configured. "
            "Set it in backend/.env."
        )

    return Settings(serpapi_key=key)
