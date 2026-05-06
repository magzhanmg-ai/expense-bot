import os
import json
import gspread
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import anthropic
from google.oauth2.service_account import Credentials

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# ВСТАВЬ СВОИ ДАННЫЕ:
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

TELEGRAM_TOKEN = "8337499162:AAFrtAB3hR4sQCwSYFQzjeFXiTYkuTLG73Y"
ANTHROPIC_API_KEY = "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"
SPREADSHEET_ID = "https://docs.google.com/spreadsheets/d/1SSCVlk8HpHw25DTpPMYyPt728AC7Xf3tZfSkG0MrZo4/edit?gid=0#gid=0"

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Google Sheets ────────────────────────────────────────────
def get_sheet():
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
    return sheet

def init_sheet():
    try:
        sheet = get_sheet()
        if not sheet.row_values(1):
            sheet.append_row(["Дата", "Сумма", "Категория", "Описание"])
            sheet.update("F1", [["Бюджет"]])
            sheet.update("F2", [[0]])
    except Exception as e:
        print(f"Ошибка таблицы: {e}")

def save_expense(amount, category, description):
    try:
        sheet = get_sheet()
        sheet.append_row([
            datetime.now().strftime("%d.%m.%Y"),
            amount,
            category,
            description
        ])
        return True
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        return False

def save_budget(amount):
    try:
        sheet = get_sheet()
        sheet.update("F1", [["Бюджет"]])
        sheet.update("F2", [[amount]])
        return True
    except Exception as e:
        print(f"Ошибка бюджета: {e}")
        return False

def get_summary():
    try:
        sheet = get_sheet()
        rows = sheet.get_all_records()
        now = datetime.now()
        month = now.strftime("%m.%Y")
        by_cat = {}
        total = 0
        for row in rows:
            date = str(row.get("Дата", ""))
            if month in date:
                amt = float(row.get("Сумма", 0) or 0)
                cat = row.get("Категория", "другое")
                total += amt
                by_cat[cat] = by_cat.get(cat, 0) + amt
        try:
            budget = float(sheet.acell("F2").value or 0)
        except:
            budget = 0
        return by_cat, total, budget
    except Exception as e:
        print(f"Ошибка чтения: {e}")
        return {}, 0, 0

# ── ИИ ──────────────────────────────────────────────────────
chat_histories = {}

SYSTEM_PROMPT = """Ты — финансовый помощник. Говоришь только по-русски. Отвечай кратко.

Когда пользователь называет расход — отвечай ТОЛЬКО JSON:
{"action": "save_expense", "amount": 500, "category": "такси", "description": "такси домой"}

Категории: еда, транспорт, коммунальные, здоровье, развлечения, одежда, другое

Когда устанавливает бюджет — отвечай ТОЛЬКО:
{"action": "save_budget", "amount": 50000}

В остальных случаях — обычный текст с эмодзи."""

async def ask_ai(user_id, text, update):
    if user_id not in chat_histories:
        chat_histories[user_id] = []

    by_cat, total, budget = get_summary()
    ctx = f"\n[Потрачено: {total:.0f}р"
    if budget:
        ctx += f", бюджет: {budget:.0f}р, осталось: {budget-total:.0f}р"
    if by_cat:
        ctx += f", категории: {', '.join(f'{k}:{v:.0f}р' for k,v in by_cat.items())}"
    ctx += "]"

    chat_histories[user_id].append({"role": "user", "content": text + ctx})

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=chat_histories[user_id]
    )
    reply = resp.content[0].text

    try:
        if reply.strip().startswith("{"):
            data = json.loads(reply.strip())

            if data.get("action") == "save_expense":
                ok = save_expense(data["amount"], data["category"], data["description"])
                by_cat, total, budget = get_summary()
                msg = f"✅ {data['description']} — {data['amount']:.0f}р ({data['category']})\n"
                msg += f"📊 Месяц: {total:.0f}р"
                if budget:
                    left = budget - total
                    msg += f"\n{'🟢' if left > 0 else '🔴'} Осталось: {left:.0f}р"
                if ok:
                    msg += "\n📋 Записано в таблицу!"
                await update.message.reply_text(msg)
                chat_histories[user_id].append({"role": "assistant", "content": msg})
                return

            elif data.get("action") == "save_budget":
                save_budget(data["amount"])
                msg = f"✅ Бюджет: {data['amount']:.0f}р — сохранён в таблицу! 📋"
                await update.message.reply_text(msg)
                chat_histories[user_id].append({"role": "assistant", "content": msg})
                return
    except:
        pass

    chat_histories[user_id].append({"role": "assistant", "content": reply})
    await update.message.reply_text(reply)

# ── Команды ──────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я финансовый помощник.\n\n"
        "Пиши о расходах:\n"
        "• «Продукты 1500р»\n"
        "• «Такси 350»\n"
        "• «Кафе 800»\n\n"
        "📌 Команды:\n"
        "/stat — статистика\n"
        "/budget 50000 — установить бюджет\n\n"
        "💾 Все данные в Google Sheets!"
    )

async def stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    by_cat, total, budget = get_summary()
    if not by_cat:
        await update.message.reply_text("📭 Расходов пока нет!")
        return
    months = ["Январь","Февраль","Март","Апрель","Май","Июнь",
              "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
    now = datetime.now()
    msg = f"📊 *{months[now.month-1]} {now.year}*\n\n"
    for cat, amt in sorted(by_cat.items(), key=lambda x: -x[1]):
        pct = amt / total * 100 if total else 0
        msg += f"• {cat}: {amt:.0f}р ({pct:.0f}%)\n"
    msg += f"\n💰 *Итого: {total:.0f}р*"
    if budget:
        left = budget - total
        msg += f"\n{'🟢' if left > 0 else '🔴'} Осталось: {left:.0f}р из {budget:.0f}р"
    msg += "\n\n📋 Смотри таблицу для диаграмм!"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def set_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(context.args[0])
        save_budget(amount)
        await update.message.reply_text(f"✅ Бюджет: {amount:.0f}р сохранён! 📋")
    except:
        await update.message.reply_text("❌ Напиши: /budget 50000")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_ai(update.effective_user.id, update.message.text, update)

# ── Запуск ───────────────────────────────────────────────────

    if __name__ == "__main__":
    init_sheet()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stat", stat))
    app.add_handler(CommandHandler("budget", set_budget))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("🚀 Бот запущен!")
    import asyncio
    asyncio.run(app.run_polling())
