"""Entry point for @Lotto8888xbot — reminders & productivity bot."""
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder

import database as db
from handlers import start, reminders, timers, list as list_handler
from scheduler import WEEKDAYS

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("lotto8888xbot")

UTC = timezone.utc


async def on_error(update, context):
    log.exception("Unhandled error: %s", context.error)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong. Please try again."
            )
    except Exception:
        pass


async def post_init(app):
    """Restore pending reminders and timers from DB into the job queue."""
    db.init_db()
    jq = app.job_queue
    now = datetime.now(UTC)

    restored_r = restored_t = 0

    for r in db.all_reminders():
        try:
            run_at = datetime.fromisoformat(r["run_at"])
            if run_at.tzinfo is None:
                run_at = run_at.replace(tzinfo=UTC)
        except Exception:
            continue

        data = {
            "chat_id": r["chat_id"], "user_id": r["user_id"],
            "text": r["text"], "reminder_id": r["id"], "repeat": r["repeat"],
        }
        job_name = f"reminder:{r['id']}"

        try:
            if r["repeat"] == "once":
                when = run_at if run_at > now else now
                jq.run_once(reminders.fire_once, when=when, data=data, name=job_name)
            elif r["repeat"] == "daily":
                jq.run_daily(
                    reminders.fire_recurring,
                    time=run_at.timetz().replace(tzinfo=UTC),
                    data=data, name=job_name,
                )
            else:  # weekly
                jq.run_daily(
                    reminders.fire_recurring,
                    time=run_at.timetz().replace(tzinfo=UTC),
                    days=(run_at.weekday(),),
                    data=data, name=job_name,
                )
            db.update_reminder_job(r["id"], job_name)
            restored_r += 1
        except Exception as e:
            log.warning("Failed to restore reminder %s: %s", r["id"], e)

    for t in db.all_timers():
        try:
            end_at = datetime.fromisoformat(t["end_at"])
            if end_at.tzinfo is None:
                end_at = end_at.replace(tzinfo=UTC)
        except Exception:
            continue
        when = end_at if end_at > now else now
        data = {
            "chat_id": t["chat_id"], "user_id": t["user_id"],
            "label": t["label"], "duration_s": t["duration_s"],
            "timer_id": t["id"],
        }
        job_name = f"timer:{t['id']}"
        try:
            jq.run_once(timers.timer_done, when=when, data=data, name=job_name)
            db.update_timer_job(t["id"], job_name)
            restored_t += 1
        except Exception as e:
            log.warning("Failed to restore timer %s: %s", t["id"], e)

    log.info("Restored %d reminders, %d timers.", restored_r, restored_t)


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN env var is required.")

    app = (
        ApplicationBuilder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    start.register(app)
    reminders.register(app)
    timers.register(app)
    list_handler.register(app)

    app.add_error_handler(on_error)

    log.info("🚀 @Lotto8888xbot starting (polling)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
