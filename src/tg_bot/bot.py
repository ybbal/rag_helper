import datetime
import os
from zoneinfo import ZoneInfo

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, JobQueue, CallbackQueryHandler

from tg_bot.handlers import start, clear, feedback, answer_by_helper, unknown, stats_command, feedback_button_handler
from tg_bot.intents import handle_sberdocs_request, handle_trip_request, handle_kprib_request
from tg_bot.statistics import reset_stats


def get_app():
    job_queue = JobQueue()
    job_queue.run_daily(
        reset_stats,
        time=datetime.time(hour=0, minute=0, second=0, tzinfo=ZoneInfo("Europe/Moscow")),
        name="daily_stats_reset"
    )

    application = (
        ApplicationBuilder()
        .token(os.getenv("TELEGRAM_BOT_TOKEN"))
        .job_queue(job_queue)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    sberdocs_pattern = r'(?i).*(сбердокс|sberdocs|инструкция).*'
    trip_pattern = r'(?i).*(командировк|инструкция по командировкам).*'
    kprib_pattern = r'(?i).*кприб.*'
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('clear', clear))
    application.add_handler(CommandHandler('feedback', feedback))
    application.add_handler(CommandHandler('stats', stats_command))

    application.add_handler(CallbackQueryHandler(feedback_button_handler))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, answer_by_helper))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(sberdocs_pattern), handle_sberdocs_request))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(trip_pattern), handle_trip_request))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(kprib_pattern), handle_kprib_request))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), answer_by_helper))
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    return application

# my_persistence = PicklePersistence(
#     filepath=str(pathlib.Path(__file__).parent.parent.parent / "storage"),
#     on_flush=False,
# )
