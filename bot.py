import finnhub
import pandas as pd

api_key = None

with open("api_key.txt") as file:
    api_key = file.read()

api_key = "sandbox_c5o0tfiad3i92b40qg70"  # TODO: remove, for testing

finnhub_client = finnhub.Client(api_key=api_key)
print(finnhub_client.stock_candles('AAPL', 'D', 1590988249, 1591852249))
