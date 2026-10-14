from datetime import datetime, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

import database as db
from scheduler import humanize_seconds

UTC = timezone.utc


def _aware(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


async def list_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = datetime.now(UTC)

    reminders = db.list_reminders(user_id)
    timers = db.list_timers(user_id)

    lines = ["📋 *Your active items*", ""]

    lines.append("*⏰ Reminders*")
    if not reminders:
        lines.append("_none_")
    else:
        for r in reminders:
            when = _aware(r["run_at"]).strftime("%Y-%m-%d %H:%M UTC")
            lines.append(f"`#{r['id']}` [{r['repeat']}] {when} — {r['text']}")

    lines.append("")
    lines.append("*⏱ Timers*")
    if not timers:
        lines.append("_none_")
    else:
        for t in timers:
            remaining = max(0, int((_aware(t["end_at"]) - now).total_seconds()))
            lines.append(
                f"`#{t['id']}` {t['label']} — {humanize_seconds(remaining)} left"
            )

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: `/cancel <id>`",
                                        parse_mode=ParseMode.MARKDOWN)
        return

    item_id = int(args[0])
    user_id = update.effective_user.id

    rem = db.get_reminder(item_id)
    if rem and rem["user_id"] == user_id:
        _remove_jobs(context, rem["job_name"])
        db.delete_reminder(item_id, user_id)
        await update.message.reply_text(f"🗑 Reminder `#{item_id}` removed.",
                                        parse_mode=ParseMode.MARKDOWN)
        return

    tmr = db.get_timer(item_id)
    if tmr and tmr["user_id"] == user_id:
        _remove_jobs(context, tmr["job_name"])
        db.delete_timer(item_id, user_id)
        await update.message.reply_text(f"🗑 Timer `#{item_id}` removed.",
                                        parse_mode=ParseMode.MARKDOWN)
        return

    await update.message.reply_text("❌ No matching reminder/timer found for you.")


def _remove_jobs(context, job_name):
    if not job_name:
        return
    for job in context.job_queue.get_jobs_by_name(job_name):
        job.schedule_removal()


def register(app):
    app.add_handler(CommandHandler("list", list_all))
    app.add_handler(CommandHandler("cancel", cancel))
