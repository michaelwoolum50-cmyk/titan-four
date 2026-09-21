import datetime as dt
import json
import requests
from titan_four.strategy import MomentumStrategy

for product in ['BTC-USD', 'ETH-USD', 'SOL-USD']:
    end = int(dt.datetime.now(dt.timezone.utc).timestamp())
    start = end - 3600*24*7
    resp = requests.get(
        f'https://api.exchange.coinbase.com/products/{product}/candles',
        params={'start': str(start), 'end': str(end), 'granularity': 300},
        timeout=30,
    )
    print('PRODUCT', product, 'status', resp.status_code)
    data = resp.json()
    print('count', len(data))
    if not data:
        continue
    closes = [float(x[4]) for x in data]
    vols = [float(x[5)] for x in data]
    s = MomentumStrategy()
    counts = {'buy': 0, 'sell': 0, 'hold': 0}
    signals = []
    for i in range(8, len(closes)-1):
        window_prices = closes[max(0, i-7):i+1]
        window_volumes = vols[max(0, i-7):i+1]
        d = s.evaluate(window_prices, window_volumes)
        counts[d.signal] += 1
        if d.signal != 'hold':
            signals.append((i, d.signal, round(d.confidence, 3), round(window_prices[0],2), round(window_prices[-1],2), round((window_prices[-1]-window_prices[0])/window_prices[0], 4)))
    print('counts', counts)
    print('signals_sample', signals[:10])
    print('price_range', round(closes[0],2), round(closes[-1],2), round((closes[-1]-closes[0])/closes[0], 4))
    print('---')
