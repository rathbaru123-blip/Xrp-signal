import os
import time
import numpy as np
import telegram
from binance.client import Client
from binance.enums import *
import ta
import pandas as pd

# Ambil API key dari environment variable
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_SECRET_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Inisialisasi Binance & Telegram
client = Client(API_KEY, API_SECRET)
bot = telegram.Bot(token=TG_TOKEN)

symbol = "XRPUSDT"
interval = Client.KLINE_INTERVAL_1H
quantity = 50  # USDT

def get_data(symbol, interval, lookback):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=lookback)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    return df

def apply_indicators(df):
    df['MA20'] = ta.trend.sma_indicator(df['close'], window=20)
    df['RSI'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    macd = ta.trend.MACD(df['close'])
    df['MACD'] = macd.macd_diff()

    # Fibonacci level (hanya contoh sederhana)
    max_price = df['high'].max()
    min_price = df['low'].min()
    diff = max_price - min_price
    df['fibo_0.618'] = max_price - diff * 0.618
    return df

def signal_generator(df):
    latest = df.iloc[-1]
    signals = []

    if latest['close'] > latest['MA20']:
        signals.append("MA Bullish")
    if latest['RSI'] < 30:
        signals.append("RSI Oversold")
    if latest['MACD'] > 0:
        signals.append("MACD Bullish")
    if latest['close'] <= latest['fibo_0.618']:
        signals.append("Near Fibo 0.618")

    if len(signals) >= 3:
        return "BUY", signals
    elif latest['RSI'] > 70 and latest['MACD'] < 0:
        return "SELL", ["RSI Overbought", "MACD Bearish"]
    else:
        return "HOLD", []

def order(symbol, side, quantity):
    try:
        if side == "BUY":
            order = client.order_market_buy(symbol=symbol, quoteOrderQty=quantity)
        else:
            order = client.order_market_sell(symbol=symbol, quoteOrderQty=quantity)
        return order
    except Exception as e:
        print("Order failed:", e)
        return None

def send_telegram(message):
    bot.send_message(chat_id=TG_CHAT_ID, text=message)

# Loop utama
while True:
    df = get_data(symbol, interval, 100)
    df = apply_indicators(df)
    action, reasons = signal_generator(df)

    print(f"Aksi: {action}, Alasan: {reasons}")
    send_telegram(f"📊 Sinyal: {action}\nAlasan: {', '.join(reasons)}")

    if action in ["BUY", "SELL"]:
        result = order(symbol, action, quantity)
        if result:
            send_telegram(f"✅ Order {action} sukses!\nHarga: {df['close'].iloc[-1]}")
        else:
            send_telegram(f"⚠️ Gagal mengeksekusi order {action}.")

    time.sleep(3600)  # Tunggu 1 jam
