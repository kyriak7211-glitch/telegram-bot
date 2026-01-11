import os
import pandas as pd
import matplotlib.pyplot as plt
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import ccxt

# Вставь сюда свой токен от BotFather
API_TOKEN = "8282166388:AAEsuwmrUzHCSoruhzbli_dA2Cqc4h0UtHw"

# Настраиваем биржу Binance
exchange = ccxt.binance()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправь тикер криптовалюты (например BTC/USDT), и я пришлю анализ графика с индикаторами."
    )

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.strip().upper()
    if "/" not in ticker:
        ticker += "/USDT"

    try:
        # Берём последние 200 часов свечей
        ohlcv = exchange.fetch_ohlcv(ticker, timeframe='1h', limit=200)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

        # Считаем индикаторы
        df["SMA_20"] = df["close"].rolling(20).mean()
        df["EMA_20"] = df["close"].ewm(span=20, adjust=False).mean()

        delta = df["close"].diff()
        up = delta.clip(lower=0)
        down = -1*delta.clip(upper=0)
        roll_up = up.rolling(14).mean()
        roll_down = down.rolling(14).mean()
        RS = roll_up / roll_down
        df["RSI"] = 100 - (100 / (1 + RS))

        last_close = df["close"].iloc[-1]
        last_rsi = df["RSI"].iloc[-1]

        # Анализ тренда
        trend = "восходящий" if df["EMA_20"].iloc[-1] > df["EMA_20"].iloc[-2] else "нисходящий"
        rsi_signal = "перепроданность" if last_rsi < 30 else "перекупленность" if last_rsi > 70 else "нейтрально"

        msg = f"📊 Анализ {ticker}:\n"
        msg += f"Последняя цена: {last_close:.2f} USDT\n"
        msg += f"Тренд (EMA20): {trend}\n"
        msg += f"RSI (14): {last_rsi:.2f} → {rsi_signal}"

        # Строим график
        plt.figure(figsize=(10,5))
        plt.plot(df["close"], label="Close")
        plt.plot(df["SMA_20"], label="SMA20")
        plt.plot(df["EMA_20"], label="EMA20")
        plt.title(f"{ticker} Цена и индикаторы")
        plt.legend()
        chart_path = f"{ticker.replace('/', '_')}.png"
        plt.savefig(chart_path)
        plt.close()

        # Отправляем текст и график пользователю
        await update.message.reply_text(msg)
        await update.message.reply_photo(open(chart_path, 'rb'))
        os.remove(chart_path)

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(API_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze))
    print("Бот запущен...")
    app.run_polling()
input("Нажми Enter для выхода...")
