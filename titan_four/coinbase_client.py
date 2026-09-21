import os
from typing import Any, Dict, Optional

import requests


class CoinbaseClient:
    """Minimal Coinbase Advanced Trade client for a no-margin asset bot."""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, passphrase: Optional[str] = None):
        self.api_key = api_key or os.getenv("COINBASE_API_KEY")
        self.api_secret = api_secret or os.getenv("COINBASE_API_SECRET")
        self.passphrase = passphrase or os.getenv("COINBASE_API_PASSPHRASE")
        self.base_url = "https://api.coinbase.com/api/v3/brokerage"

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["CB-ACCESS-KEY"] = self.api_key
        if self.api_secret:
            headers["CB-ACCESS-SIGN"] = self.api_secret
        if self.passphrase:
            headers["CB-ACCESS-PASSPHRASE"] = self.passphrase
        return headers

    def get_accounts(self) -> Dict[str, Any]:
        response = requests.get(f"{self.base_url}/accounts", headers=self._headers(), timeout=20)
        response.raise_for_status()
        return response.json()

    def get_product(self, product_id: str) -> Dict[str, Any]:
        response = requests.get(f"{self.base_url}/products/{product_id}/ticker", headers=self._headers(), timeout=20)
        response.raise_for_status()
        return response.json()

    def place_market_order(self, product_id: str, side: str, size: float) -> Dict[str, Any]:
        payload = {
            "client_order_id": f"titan-four-{side}-{product_id}",
            "product_id": product_id,
            "side": side,
            "order_configuration": {
                "market_market_ioc": {
                    "quote_size": str(size) if side == "BUY" else None,
                    "base_size": str(size) if side == "SELL" else None,
                }
            },
        }
        payload["order_configuration"]["market_market_ioc"] = {
            k: v for k, v in payload["order_configuration"]["market_market_ioc"].items() if v is not None
        }
        response = requests.post(f"{self.base_url}/orders", json=payload, headers=self._headers(), timeout=20)
        response.raise_for_status()
        return response.json()
