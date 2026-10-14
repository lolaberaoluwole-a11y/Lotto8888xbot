from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

HELP_TEXT = (
    "👋 *Welcome to Lotto8888xBot!*\n"
    "Your reminders & productivity companion.\n\n"
    "*Commands*\n"
    "• `/remind <when> | <text>` — one-time reminder\n"
    "   e.g. `/remind +10m | take a break`\n"
    "   e.g. `/remind 14:30 | call mom`\n"
    "   e.g. `/remind 2026-01-30 14:00 | meeting`\n\n"
    "• `/daily <HH:MM> | <text>` — daily alert\n"
    "   e.g. `/daily 08:00 | standup`\n\n"
    "• `/weekly <Mon HH:MM> | <text>` — weekly alert\n"
    "   e.g. `/weekly Mon 09:00 | weekly review`\n\n"
    "• `/timer <duration> [label]` — study timer\n"
    "   e.g. `/timer 25m Pomodoro`\n\n"
    "• `/list` — view active reminders & timers\n"
    "• `/cancel <id>` — remove a reminder or timer\n"
    "• `/help` — show this message\n\n"
    "⚠️ All times are UTC."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN)


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive.")


def register(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("ping", ping))
