import ccxt
import pandas as pd
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Вставь сюда токен от BotFather
TOKEN = "8386137295:AAHRqu4lM-6GcJJpcGWAwKrPA38cLrljXrc"

# Флаг пользователей, которые нажали /start
user_started = {}

# Таймфрейм
TIMEFRAME = '1h'

# Подключение к Binance
exchange = ccxt.binance({'enableRateLimit': True})

# Получаем все пары USDT
def get_usdt_pairs():
    markets = exchange.load_markets()
    pairs = [symbol for symbol in markets if symbol.endswith("/USDT")]
    return pairs

MONETES = get_usdt_pairs()
# Индекс текущей монеты для каждого пользователя
user_index = {}

# Приветствие до /start
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if not user_started.get(chat_id):
        await update.message.reply_text(
            "👋 Привет! Я твой крипто-помощник.\n"
            "Я могу давать торговые сигналы LONG и SHORT с рассчитанными Entry, Stop Loss и Take Profit.\n"
            "Нажмите /start, чтобы активировать бота."
        )

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_started[chat_id] = True
    user_index[chat_id] = 0  # начинаем с первой монеты
    await update.message.reply_text(
        f"✅ Бот запущен! Теперь вы можете писать 'TRADE', чтобы получить сигналы по одной монете за раз."
    )

# Анализ монеты
def analyze_pair(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
        df['EMA200'] = df['close'].ewm(span=200).mean()
        df['RSI'] = 100 - (100 / (1 + df['close'].diff().clip(lower=0).rolling(14).mean() / df['close'].diff().clip(upper=0).abs().rolling(14).mean()))

        last = df.iloc[-1]
        entry = last['close']
        ema200 = last['EMA200']
        rsi = last['RSI']

        # Логика сигнала
        if entry > ema200:
            direction = "LONG"
            stop_loss = entry * 0.985
            take_profit = entry * 1.045
        else:
            direction = "SHORT"
            stop_loss = entry * 1.015
            take_profit = entry * 0.955

        return {
            "pair": symbol,
            "direction": direction,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "rsi": rsi
        }

    except Exception as e:
        print(f"Error {symbol}: {e}")
        return None

# Обработка текста
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip().lower()

    if not user_started.get(chat_id):
        await welcome(update, context)
        return

    if text == "trade":
        index = user_index.get(chat_id, 0)
        symbol = MONETES[index % len(MONETES)]  # берём следующую монету
        signal = analyze_pair(symbol)

        if signal:
            text_msg = (
                f"📊 SIGNAL\nPair: {signal['pair']}\nDirection: {signal['direction']}\n"
                f"Entry: {signal['entry']:.6f}\nStop Loss: {signal['stop_loss']:.6f}\nTake Profit: {signal['take_profit']:.6f}\n"
                f"RSI: {signal['rsi']:.2f}\nNot financial advice"
            )
            await update.message.reply_text(text_msg)
        else:
            await update.message.reply_text(f"Не удалось получить сигнал для {symbol}")

        # Увеличиваем индекс на 1 для следующей команды
        user_index[chat_id] = index + 1
    else:
        await update.message.reply_text("Напишите 'TRADE', чтобы получить торговой сигнал по одной монете.")

# Основной запуск
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Бот запущен...")
    app.run_polling()
