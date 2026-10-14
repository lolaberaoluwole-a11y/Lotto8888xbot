from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

import database as db
from scheduler import parse_duration_seconds, humanize_seconds

UTC = timezone.utc


async def timer_done(context: ContextTypes.DEFAULT_TYPE):
    d = context.job.data
    try:
        await context.bot.send_message(
            chat_id=d["chat_id"],
            text=(f"⏱ *Timer finished:* {d['label']}\n"
                  f"Duration: {humanize_seconds(d['duration_s'])}"),
            parse_mode=ParseMode.MARKDOWN,
        )
    finally:
        db.delete_timer(d["timer_id"], d["user_id"])


async def timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    args = context.args or []
    if not args:
        await msg.reply_text(
            "Usage: `/timer <duration> [label]`\nExample: `/timer 25m Pomodoro`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    duration_s = parse_duration_seconds(args[0])
    if not duration_s or duration_s <= 0:
        await msg.reply_text("❌ Invalid duration. Examples: `25m`, `1h30m`, `90s`.",
                             parse_mode=ParseMode.MARKDOWN)
        return

    label = " ".join(args[1:]).strip() or "Study session"
    end_at = datetime.now(UTC) + timedelta(seconds=duration_s)

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    tid = db.add_timer(chat_id, user_id, label, duration_s, end_at.isoformat())
    job_name = f"timer:{tid}"
    context.job_queue.run_once(
        timer_done, when=end_at,
        data={"chat_id": chat_id, "user_id": user_id, "label": label,
              "duration_s": duration_s, "timer_id": tid},
        name=job_name,
    )
    db.update_timer_job(tid, job_name)

    await msg.reply_text(
        f"⏱ Timer *#{tid}* started — {humanize_seconds(duration_s)}\n"
        f"_{label}_\nEnds: `{end_at.strftime('%Y-%m-%d %H:%M UTC')}`",
        parse_mode=ParseMode.MARKDOWN,
    )


def register(app):
    app.add_handler(CommandHandler("timer", timer))
