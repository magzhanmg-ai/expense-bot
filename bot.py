import os
import json
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import anthropic

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── База данных ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            category TEXT,
            description TEXT,
            date TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS budget (
            user_id INTEGER PRIMARY KEY,
            monthly_budget REAL
        )
    """)
    conn.commit()
    conn.close()

def get_expenses_summary(user_id):
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    now = datetime.now()
    month_start = f"{now.year}-{now.month:02d}-01"
    c.execute("""
        SELECT category, SUM(amount), COUNT(*)
        FROM expenses
        WHERE user_id=? AND date >= ?
        GROUP BY category
    """, (user_id, month_start))
    rows = c.fetchall()
    total = sum(r[1] for r in rows)
    c.execute("SELECT monthly_budget FROM budget WHERE user_id=?", (user_id,))
    budget_row = c.fetchone()
    budget = budget_row[0] if budget_row else None
    conn.close()
    return rows, total, budget

def save_expense(user_id, amount, category, description):
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO expenses (user_id, amount, category, description, date)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, amount, category, description, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def save_budget(user_id, amount):
    conn = sqlite3.connect("expenses.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO budget (user_id, monthly_budget) VALUES (?, ?)", (user_id, amount))
    conn.commit()
    conn.close()

# ── История чатов ────────────────────────────────────────────
chat_histories = {}

SYSTEM_PROMPT = """Ты — личный финансовый помощник для учёта расходов и бюджета. Говоришь только по-русски.

Твои задачи:
1. Записывать расходы когда пользователь их называет
2. Показывать статистику и итоги
3. Следить за месячным бюджетом
4. Давать советы по экономии

Когда пользователь называет расход — сразу выдели:
- сумму (число)
- категорию (еда, транспорт, коммунальные, здоровье, развлечения, одежда, другое)
- описание

Отвечай в формате JSON ТОЛЬКО когда нужно записать расход:
{"action": "save_expense", "amount": 500, "category": "еда", "description": "продукты"}

Когда пользователь устанавливает бюджет:
{"action": "save_budget", "amount": 50000}

В остальных случаях отвечай обычным текстом с эмодзи. Будь дружелюбным и кратким."""

async def process_ai_response(user_id, text, update):
    if user_id not in chat_histories:
        chat_histories[user_id] = []

    # Добавляем контекст о текущих расходах
    rows, total, budget = get_expenses_summary(user_id)
    context = f"\n[Контекст: потрачено в этом месяце {total:.0f}р"
    if budget:
        left = budget - total
        context += f", бюджет {budget:.0f}р, осталось {left:.0f}р"
    if rows:
        context += f", категории: {', '.join(f'{r[0]}:{r[1]:.0f}р' for r in rows)}"
    context += "]"

    chat_histories[user_id].append({
        "role": "user",
        "content": text + context
    })

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=chat_histories[user_id]
    )

    reply = response.content[0].text

    # Проверяем — вдруг это JSON команда
    try:
        clean = reply.strip()
        if clean.startswith("{"):
            data = json.loads(clean)
            if data.get("action") == "save_expense":
                save_expense(user_id, data["amount"], data["category"], data["description"])
                rows, total, budget = get_expenses_summary(user_id)
                msg = f"✅ Записал: {data['description']} — {data['amount']:.0f}р ({data['category']})\n"
                msg += f"📊 Итого за месяц: {total:.0f}р"
                if budget:
                    left = budget - total
                    emoji = "🟢" if left > 0 else "🔴"
                    msg += f"\n{emoji} Остаток бюджета: {left:.0f}р из {budget:.0f}р"
                await update.message.reply_text(msg)
                chat_histories[user_id].append({"role": "assistant", "content": msg})
                return
            elif data.get("action") == "save_budget":
                save_budget(user_id, data["amount"])
                msg = f"✅ Бюджет на месяц установлен: {data['amount']:.0f}р"
                await update.message.reply_text(msg)
                chat_histories[user_id].append({"role": "assistant", "content": msg})
                return
    except:
        pass

    chat_histories[user_id].append({"role": "assistant", "content": reply})
    await update.message.reply_text(reply)

# ── Команды ──────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Привет! Я твой финансовый помощник.\n\n"
        "Просто пиши мне о расходах обычными словами:\n"
        "• «Купил продукты на 1500р»\n"
        "• «Заплатил за интернет 600 рублей»\n"
        "• «Такси 350р»\n\n"
        "📌 Полезные команды:\n"
        "/stat — статистика за месяц\n"
        "/budget 50000 — установить бюджет на месяц\n\n"
        "С чего начнём? 😊"
    )
    await update.message.reply_text(text)

async def stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    rows, total, budget = get_expenses_summary(user_id)
    if not rows:
        await update.message.reply_text("📭 Расходов пока нет. Напиши мне о первой трате!")
        return
    now = datetime.now()
    msg = f"📊 *Расходы за {now.strftime('%B %Y')}*\n\n"
    for cat, amount, count in sorted(rows, key=lambda x: -x[1]):
        msg += f"• {cat}: {amount:.0f}р ({count} раз)\n"
    msg += f"\n💰 *Итого: {total:.0f}р*"
    if budget:
        left = budget - total
        pct = (total / budget * 100)
        emoji = "🟢" if left > 0 else "🔴"
        msg += f"\n{emoji} Бюджет: {budget:.0f}р | Осталось: {left:.0f}р ({pct:.0f}% потрачено)"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def set_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        amount = float(context.args[0])
        save_budget(user_id, amount)
        await update.message.reply_text(f"✅ Бюджет на месяц: {amount:.0f}р\nБуду следить за расходами!")
    except:
        await update.message.reply_text("❌ Напиши так: /budget 50000")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    await process_ai_response(user_id, text, update)

# ── Запуск ───────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stat", stat))
    app.add_handler(CommandHandler("budget", set_budget))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен!")
    app.run_polling()
