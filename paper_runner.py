import datetime as dt
import json
import os
import time
from typing import Any, List

import requests

from titan_four.backtest import MomentumBacktest
from titan_four.paper_trading import LiveReadinessGate

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
CACHE_TTL_SECONDS = 6 * 3600  # 6 hours


def _cache_path(product_id: str, granularity: int, hours: int) -> str:
    safe_product = product_id.replace("/", "_")
    return os.path.join(
        CACHE_DIR, f"{safe_product}_{int(granularity)}_{int(hours)}.json"
    )


def _load_cache(path: str):
    try:
        if os.path.isfile(path) and (time.time() - os.path.getmtime(path)) < CACHE_TTL_SECONDS:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            closes = payload.get("closes")
            volumes = payload.get("volumes")
            if isinstance(closes, list) and isinstance(volumes, list) and closes:
                return [float(c) for c in closes], [float(v) for v in volumes]
    except (OSError, ValueError, TypeError):
        pass
    return None


def _write_cache(path: str, closes: List[float], volumes: List[float]) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump({"closes": closes, "volumes": volumes}, fh)
        os.replace(tmp_path, path)
    except OSError:
        pass


def summarize_result(product_id: str, result: dict[str, Any]) -> dict[str, Any]:
    gate = LiveReadinessGate()
    report = gate.score(
        net_return=float(result.get("net_return", 0.0)),
        max_drawdown=float(result.get("max_drawdown", 1.0)),
        win_rate=float(result.get("win_rate", 0.0)),
        trades=int(result.get("trades", 0)),
        scenarios_passed=int(result.get("scenarios_passed", 0)),
    )
    return {
        "product": product_id,
        "ready": report.ready,
        "score": report.score,
        "reasons": report.reasons,
    }


def fetch_candles(product_id: str, granularity: int = 300, hours: int = 24):
    cache_path = _cache_path(product_id, granularity, hours)
    cached = _load_cache(cache_path)
    if cached is not None:
        return cached

    max_candles = 300
    max_hours = max(1, max_candles * granularity // 3600)

    end = dt.datetime.now(dt.timezone.utc)
    requested_start = end - dt.timedelta(hours=hours)
    all_closes = []
    all_volumes = []

    current_end = end
    while current_end > requested_start:
        chunk_hours = min(max_hours, int((current_end - requested_start).total_seconds() // 3600) or 1)
        chunk_start = current_end - dt.timedelta(hours=chunk_hours)
        url = f"https://api.exchange.coinbase.com/products/{product_id}/candles"
        params = {
            "start": str(int(chunk_start.timestamp())),
            "end": str(int(current_end.timestamp())),
            "granularity": granularity,
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        closes = [float(item[4]) for item in data]
        volumes = [float(item[5]) for item in data]
        if all_closes:
            all_closes.extend(closes[1:])
            all_volumes.extend(volumes[1:])
        else:
            all_closes.extend(closes)
            all_volumes.extend(volumes)
        current_end = chunk_start

    if not all_closes:
        raise ValueError(f"No candle data returned for {product_id}")
    # Coinbase returns candles newest-first; reverse to chronological
    # (oldest-first) order before returning and caching.
    all_closes = all_closes[::-1]
    all_volumes = all_volumes[::-1]
    _write_cache(cache_path, all_closes, all_volumes)
    return all_closes, all_volumes


def main():
    product_id = "BTC-USD"
    closes, volumes = fetch_candles(product_id, granularity=300, hours=48)
    backtest = MomentumBacktest(starting_cash=10000.0, position_fraction=0.2)
    result = backtest.run(closes, volumes)
    report = summarize_result(
        product_id,
        {
            "trades": result.trades,
            "wins": result.wins,
            "losses": result.losses,
            "net_return": result.net_return,
            "win_rate": result.win_rate,
            "max_drawdown": result.max_drawdown,
            "scenarios_passed": 0,
        },
    )
    print({
        "product": product_id,
        "samples": len(closes),
        "trades": result.trades,
        "wins": result.wins,
        "losses": result.losses,
        "net_return": round(result.net_return, 6),
        "win_rate": round(result.win_rate, 4),
        "max_drawdown": round(result.max_drawdown, 6),
        "final_value": round(result.final_value, 2),
        "live_readiness": report,
    })


if __name__ == "__main__":
    main()
