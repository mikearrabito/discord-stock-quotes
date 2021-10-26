import finnhub
import pandas as pd

api_key = None

with open("api_key.txt") as file:
    api_key = file.read()

finnhub_client = finnhub.Client(api_key=api_key)
print(finnhub_client.stock_candles('AAPL', 'D', 1590988249, 1591852249))
