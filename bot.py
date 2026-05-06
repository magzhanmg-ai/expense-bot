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

# Содержимое JSON файла от Google — вставь всё между тройными кавычками:
GOOGLE_CREDENTIALS_JSON = """{
  "type": "service_account",
  "project_id": "promising-life-226919",
  "private_key_id": "2f992edca137534724f50de554baec9500212d98",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCtUdEWpsFMpc35\n029FrxGfSExfg3L2eCg6MVSUO70VZTESbvSldLqguK3TGPCAnTCIvAlLFIgascQu\nvJAAQ2+gmiamqGGcMNSbhp+6VozUOMg3li3VsZzWRbYjXFjhMyh6g6Z6rmihClFt\nLwYekwiJfNfNo3jWaff99MuSWa6l7sP86k6sgNM6/YLkXX5un6net3YKUu2KZemZ\nL3pzypPHg3qyHfPYJhmGyVa5uatDhotjUa3DOv3/YD0r1BuLib1qQCeWg51C6vie\n3sQqj6C3Ti+VBsE9cODOk/yoSd0ysUZuqqGqBFEe7+v3WsAm+ayP3wp1YwBJUTnH\nstezy8wdAgMBAAECggEADKZaT6ArnwvB8RAywKACtgCpnFYEe8Mw0nB7xxbmGcvp\nLTp+bh4LKgRYoX3iPczbODubJQjyVxpu4mdeTjqdyNe/Zu4Gs8bnmZNVkJzVCf87\n87ypCz37n7L2VHXewc8BTxHRQoZ8ufY+E605Md2S47ACMy7ReLrCwB0QB5Y2lkMs\ndPYb8kIkv/sijj9+dJ/bZcjzwz5lcWrBb6A026TaU2nh6cKVtahEIZ/Q6vvuerdg\nEHfdV/TllB2/nfQzhWQQOB+9UBE5klIjZUP/EzWWWJuAyYsiO7fQiaxjtaWE3KwK\n5J79M2nHh2T8kMmWphE9HaxwRysigch+A5s7sfNuMQKBgQDZT+iamM0MHsHIlzts\nQ83uZcOS6cNG0OfstRkgjrTfIB55iOkIC2uY4OXnWc1ZATP+RvpMHyuRmMYuLAyB\nm+rT/V1b3HiHF4ft9bXITXqXAdkROJY2UkkEhX6SlczzLjWIPCUv3/4sl7+25YSk\nBgY2FCtnepo2VrXvGpR9XiP/UQKBgQDMLO31npGXY/TWohEbilKRQDq7XVn5V8Rm\nwpN7ZKAR87COs1sHbg2CmA5o0NhfqG7m304zDDzVVvFq7CXFcWObDGsMSEVc0EVk\nr81n9pNoxt97Zz3Ut6PaVSgE0tqMDYGxjs9CG6Sor8hQRR0e/0C1kyCQ5cFvD8MA\nRy0ikfdFDQKBgQCSXMuhNEEGZMDHxXP0W0abxlaO4Hrxe0p5lw+xaexQS2W7HYc2\nL9rsQK0XwNgZlkHahRuXoXbKvUbdWjWiJc1nskHq2PckpaibkN46ZlSm2EvG2YHy\nXEFpli/FsrczInBTrY6uTAL5Lcul97f6cURFsBf7vguXhZdLz28rcPh1wQKBgFkf\nd5OSbtzVbedOgQczfs0Wa0yj+AVGEV4FqxjemJydccEoeyCoIk+SDiAkoX5H6Hjw\nmpLf0aISPHk+sVIZJ7BjYErRNS3JX7EOqCusTzYaMS0NqMi0jFped4R7gZhGwQj/\nXGrv5BUZ/edD8+024Ekh+sIk+CWBjM4PQ51md7f1AoGASL4qOoGpOjpy+cueUUpV\njJWmOsXb2rLD+qvLJgGAJHHkIBAl0U6z5Ua8AuJISjD84geFdSJ6pq/EYFUF9fJJ\nPiA60Unnhq1VjYiBE1EDNAggFaP38QwBLDTvwXs87qhtUdwCao9Q3ufMFnibYPVK\n8KnLNikl2Ifk3Kpj3eQFp5I=\n-----END PRIVATE KEY-----\n",
  "client_email": "expense-bot@promising-life-226919.iam.gserviceaccount.com",
  "client_id": "115733687066325693079",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/expense-bot%40promising-life-226919.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

"""

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# Подключение к Google Sheets
def get_sheet():
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return sheet

def init_sheet():
    try:
        sheet = get_sheet()
        headers = sheet.row_values(1)
        if not headers:
            sheet.append_row(["Дата", "Сумма", "Категория", "Описание", "Бюджет"])
    except Exception as e:
        print(f"Ошибка инициализации таблицы: {e}")

def save_expense_to_sheet(amount, category, description):
    try:
        sheet = get_sheet()
        sheet.append_row([
            datetime.now().strftime("%d.%m.%Y"),
            amount,
            category,
            description,
            ""
        ])
        return True
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        return False

def save_budget_to_sheet(amount):
    try:
        sheet = get_sheet()
        # Записываем бюджет в отдельную ячейку G1
        sheet.update("G1", [["Бюджет на месяц"]])
        sheet.update("G2", [[amount]])
        return True
    except Exception as e:
        print(f"Ошибка сохранения бюджета: {e}")
        return False

def get_monthly_summary():
    try:
        sheet = get_sheet()
        all_rows = sheet.get_all_records()
        now = datetime.now()
        current_month = now.strftime("%m.%Y")

        expenses_by_category = {}
        total = 0

        for row in all_rows:
            date_str = str(row.get("Дата", ""))
            if current_month in date_str:
                amount = float(row.get("Сумма", 0) or 0)
                category = row.get("Категория", "другое")
                total += amount
                expenses_by_category[category] = expenses_by_category.get(category, 0) + amount

        # Получаем бюджет
        try:
            budget = float(sheet.acell("G2").value or 0)
        except:
            budget = 0

        return expenses_by_category, total, budget
    except Exception as e:
        print(f"Ошибка получения данных: {e}")
        return {}, 0, 0

# ── Anthropic клиент ─────────────────────────────────────────
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

chat_histories = {}

SYSTEM_PROMPT = """Ты — личный финансовый помощник для учёта расходов и бюджета. Говоришь только по-русски.

Когда пользователь называет расход — отвечай ТОЛЬКО в формате JSON:
{"action": "save_expense", "amount": 500, "category": "такси", "description": "такси домой"}

Категории: еда, транспорт, коммунальные, здоровье, развлечения, одежда, другое

Когда пользователь устанавливает бюджет — отвечай ТОЛЬКО:
{"action": "save_budget", "amount": 50000}

В остальных случаях (вопросы, статистика, советы) — отвечай обычным текстом с эмодзи. Кратко и по делу."""

async def process_ai_response(user_id, text, update):
    if user_id not in chat_histories:
        chat_histories[user_id] = []

    expenses, total, budget = get_monthly_summary()
    context = f"\n[Контекст: потрачено в этом месяце {total:.0f}р"
    if budget:
        left = budget - total
        context += f", бюджет {budget:.0f}р, осталось {left:.0f}р"
    if expenses:
        context += f", по категориям: {', '.join(f'{k}:{v:.0f}р' for k,v in expenses.items())}"
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

    try:
        clean = reply.strip()
        if clean.startswith("{"):
            data = json.loads(clean)

            if data.get("action") == "save_expense":
                saved = save_expense_to_sheet(data["amount"], data["category"], data["description"])
                expenses, total, budget = get_monthly_summary()
                msg = f"✅ Записал: {data['description']} — {data['amount']:.0f}р ({data['category']})\n"
                msg += f"📊 Итого за месяц: {total:.0f}р"
                if budget:
                    left = budget - total
                    emoji = "🟢" if left > 0 else "🔴"
                    msg += f"\n{emoji} Остаток: {left:.0f}р из {budget:.0f}р"
                if saved:
                    msg += "\n📋 Сохранено в таблицу!"
                await update.message.reply_text(msg)
                chat_histories[user_id].append({"role": "assistant", "content": msg})
                return

            elif data.get("action") == "save_budget":
                save_budget_to_sheet(data["amount"])
                msg = f"✅ Бюджет на месяц: {data['amount']:.0f}р\nБуду следить за расходами! 📋"
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
        "Пиши о расходах обычными словами:\n"
        "• «Купил продукты на 1500р»\n"
        "• «Такси 350р»\n"
        "• «Кафе 800 тенге»\n\n"
        "📌 Команды:\n"
        "/stat — статистика за месяц\n"
        "/budget 50000 — установить бюджет\n\n"
        "Все данные сохраняются в Google Sheets 📊"
    )
    await update.message.reply_text(text)

async def stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    expenses, total, budget = get_monthly_summary()
    if not expenses:
        await update.message.reply_text("📭 Расходов пока нет. Напиши мне о первой трате!")
        return
    now = datetime.now()
    months = ["Январь","Февраль","Март","Апрель","Май","Июнь",
              "Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"]
    msg = f"📊 *{months[now.month-1]} {now.year}*\n\n"
    for cat, amount in sorted(expenses.items(), key=lambda x: -x[1]):
        pct = (amount / total * 100) if total > 0 else 0
        msg += f"• {cat}: {amount:.0f}р ({pct:.0f}%)\n"
    msg += f"\n💰 *Итого: {total:.0f}р*"
    if budget:
        left = budget - total
        emoji = "🟢" if left > 0 else "🔴"
        msg += f"\n{emoji} Бюджет: {budget:.0f}р | Осталось: {left:.0f}р"
    msg += "\n\n📋 Все данные в Google Sheets"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def set_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(context.args[0])
        save_budget_to_sheet(amount)
        await update.message.reply_text(f"✅ Бюджет на месяц: {amount:.0f}р\nСохранено в таблицу! 📋")
    except:
        await update.message.reply_text("❌ Напиши так: /budget 50000")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    await process_ai_response(user_id, text, update)

# ── Запуск ───────────────────────────────────────────────────
if __name__ == "__main__":
    init_sheet()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stat", stat))
    app.add_handler(CommandHandler("budget", set_budget))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен с Google Sheets! 🚀")
    app.run_polling()
