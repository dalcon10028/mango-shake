from functools import lru_cache
from typing import List

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Strategy0458Settings(BaseModel):
    """거래 전략 설정"""
    division_count: int = 5
    symbol: str = 'SOLUSDT'
    profit_target_rate: float = 1.05
    partial_close_ratio: float = 0.5
    min_profit_rate: float = 0.3

class Settings(BaseSettings):
    db_url: str = ''
    strategy_0458: Strategy0458Settings =  Strategy0458Settings()

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

@lru_cache
def get_settings():
    return Settings()