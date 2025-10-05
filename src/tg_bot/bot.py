import os

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from tg_bot.handlers import start, clear, feedback, answer_by_helper, handle_sberdocs_request, handle_trip_request, \
    handle_kprib_request, unknown


def get_app():
    application = (
        ApplicationBuilder()
        .token(os.getenv("TELEGRAM_BOT_TOKEN"))
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
