from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

import database as db
from scheduler import parse_when, WEEKDAYS

UTC = timezone.utc


# ---------- Job callbacks ----------
async def fire_once(context: ContextTypes.DEFAULT_TYPE):
    d = context.job.data
    try:
        await context.bot.send_message(
            chat_id=d["chat_id"],
            text=f"⏰ *Reminder:* {d['text']}",
            parse_mode=ParseMode.MARKDOWN,
        )
    finally:
        db.delete_reminder(d["reminder_id"], d["user_id"])


async def fire_recurring(context: ContextTypes.DEFAULT_TYPE):
    d = context.job.data
    await context.bot.send_message(
        chat_id=d["chat_id"],
        text=f"🔁 *{d['repeat'].capitalize()} reminder:* {d['text']}",
        parse_mode=ParseMode.MARKDOWN,
    )


# ---------- /remind ----------
async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    raw = msg.text or ""
    if "|" not in raw:
        await msg.reply_text(
            "Usage: `/remind <when> | <text>`\nExample: `/remind +10m | drink water`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    left, text = raw.split("|", 1)
    # strip leading command token
    parts = left.split(maxsplit=1)
    when_str = parts[1].strip() if len(parts) > 1 else ""
    text = text.strip()

    if not when_str or not text:
        await msg.reply_text("❌ Need both a time and text.")
        return

    when = parse_when(when_str)
    if when is None:
        await msg.reply_text(
            "❌ Couldn't parse that time. Try `+10m`, `14:30`, or `2026-02-01 09:00`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return
    if when <= datetime.now(UTC):
        await msg.reply_text("⏳ That time is in the past — pick a future time.")
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    rid = db.add_reminder(chat_id, user_id, text, when.isoformat(), "once")
    job_name = f"reminder:{rid}"
    context.job_queue.run_once(
        fire_once, when=when,
        data={"chat_id": chat_id, "user_id": user_id, "text": text,
              "reminder_id": rid},
        name=job_name,
    )
    db.update_reminder_job(rid, job_name)

    await msg.reply_text(
        f"✅ Reminder *#{rid}* set for `{when.strftime('%Y-%m-%d %H:%M UTC')}`:\n_{text}_",
        parse_mode=ParseMode.MARKDOWN,
    )


# ---------- /daily & /weekly ----------
async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _schedule_recurring(update, context, "daily")


async def weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _schedule_recurring(update, context, "weekly")


async def _schedule_recurring(update, context, repeat):
    msg = update.effective_message
    raw = msg.text or ""
    if "|" not in raw:
        example = ("`/daily 08:00 | standup`" if repeat == "daily"
                   else "`/weekly Mon 09:00 | weekly review`")
        await msg.reply_text(f"Usage example: {example}", parse_mode=ParseMode.MARKDOWN)
        return

    left, text = raw.split("|", 1)
    parts = left.split(maxsplit=1)
    schedule = parts[1].strip() if len(parts) > 1 else ""
    text = text.strip()

    if not schedule or not text:
        await msg.reply_text("❌ Need both a schedule and text.")
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    if repeat == "daily":
        if ":" not in schedule:
            await msg.reply_text("❌ Daily format: `HH:MM` in UTC.", parse_mode=ParseMode.MARKDOWN)
            return
        try:
            hh, mm = map(int, schedule.split(":"))
            if not (0 <= hh < 24 and 0 <= mm < 60):
                raise ValueError
        except ValueError:
            await msg.reply_text("❌ Invalid time. Use `HH:MM`.")
            return
        first = _next_daily(hh, mm)
        # register with run_daily using time-of-day
        job_name = f"daily:{user_id}:{hh:02d}{mm:02d}"
        context.job_queue.run_daily(
            fire_recurring,
            time=first.timetz().replace(tzinfo=UTC),
            data={"chat_id": chat_id, "user_id": user_id,
                  "text": text, "repeat": "daily"},
            name=job_name,
        )
    else:  # weekly
        tokens = schedule.split()
        if len(tokens) != 2 or tokens[0].lower()[:3] not in WEEKDAYS or ":" not in tokens[1]:
            await msg.reply_text("❌ Weekly format: `Mon HH:MM` (UTC).",
                                 parse_mode=ParseMode.MARKDOWN)
            return
        wd = WEEKDAYS[tokens[0].lower()[:3]]
        try:
            hh, mm = map(int, tokens[1].split(":"))
            if not (0 <= hh < 24 and 0 <= mm < 60):
                raise ValueError
        except ValueError:
            await msg.reply_text("❌ Invalid time. Use `HH:MM`.")
            return
        first = _next_weekly(wd, hh, mm)
        job_name = f"weekly:{user_id}:{wd}:{hh:02d}{mm:02d}"
        context.job_queue.run_daily(
            fire_recurring,
            time=first.timetz().replace(tzinfo=UTC),
            days=(wd,),
            data={"chat_id": chat_id, "user_id": user_id,
                  "text": text, "repeat": "weekly"},
            name=job_name,
        )

    rid = db.add_reminder(chat_id, user_id, text, first.isoformat(), repeat, job_name)
    await msg.reply_text(
        f"✅ *{repeat.capitalize()}* reminder *#{rid}* scheduled.\n"
        f"Next: `{first.strftime('%Y-%m-%d %H:%M UTC')}`\n_{text}_",
        parse_mode=ParseMode.MARKDOWN,
    )


def _next_daily(hh, mm):
    now = datetime.now(UTC)
    t = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if t <= now:
        t += timedelta(days=1)
    return t


def _next_weekly(wd, hh, mm):
    now = datetime.now(UTC)
    days_ahead = (wd - now.weekday()) % 7
    t = (now + timedelta(days=days_ahead)).replace(
        hour=hh, minute=mm, second=0, microsecond=0
    )
    if t <= now:
        t += timedelta(days=7)
    return t


def register(app):
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("weekly", weekly))
