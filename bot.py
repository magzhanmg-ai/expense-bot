import os
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("TELEGRAM_TOKEN")

GOOGLE_SHEET_NAME = "FinanceBot"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json",
    scope
)

client = gspread.authorize(creds)

sheet = client.open(GOOGLE_SHEET_NAME).sheet1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Финансовый ассистент готов 🚀"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    records = sheet.get_all_records()

    income = 0
    expense = 0

    for row in records:
        if row["Тип"] == "доход":
            income += int(row["Сумма"])

        if row["Тип"] == "расход":
            expense += int(row["Сумма"])

    balance = income - expense

    text = (
        f"Доходы: {income} ₸\n"
        f"Расходы: {expense} ₸\n"
        f"Баланс: {balance} ₸"
    )

    await update.message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.lower()

    parts = text.split()

    if len(parts) < 2:
        await update.message.reply_text(
            "Формат:\nеда 4500"
        )
        return

    category = parts[0]
    amount = parts[1]

    if not amount.isdigit():
        await update.message.reply_text(
            "Сумма должна быть числом"
        )
        return

    amount = int(amount)

    expense_categories = [
        "еда",
        "такси",
        "спорт",
        "кредит",
        "развлечения",
        "здоровье"
    ]

    income_categories = [
        "зарплата",
        "бизнес",
        "доход"
    ]

    operation_type = "расход"

    if category in income_categories:
        operation_type = "доход"

    sheet.append_row([
        str(datetime.now()),
        operation_type,
        category,
        amount
    ])

    await update.message.reply_text(
        f"Записано ✅\n"
        f"{category}: {amount} ₸"
    )


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

print("Bot started...")

app.run_polling()
