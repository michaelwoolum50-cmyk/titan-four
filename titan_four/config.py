import os
from dataclasses import dataclass


@dataclass
class Config:
    api_key: str = os.getenv("COINBASE_API_KEY", "")
    api_secret: str = os.getenv("COINBASE_API_SECRET", "")
    passphrase: str = os.getenv("COINBASE_API_PASSPHRASE", "")
    product_ids: list[str] = None
    dry_run: bool = True
    allow_live_trading: bool = False
    max_position_fraction: float = 0.2
    max_positions: int = 3
    leverage_allowed: bool = False

    def __post_init__(self):
        if self.product_ids is None:
            self.product_ids = ["BTC-USD", "ETH-USD", "SOL-USD"]


DEFAULT_CONFIG = Config()
