import logging
import os
import pathlib
from asyncio import sleep

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from giga_helper.helper import GigaHelper
from giga_helper.settings import GigaSettings

logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.WARN,
    force=True,
    handlers=[
        logging.FileHandler(str(pathlib.Path(__file__).parent.parent.parent / os.getenv("LOG_FILE")), encoding="UTF-8"),
        logging.StreamHandler()
    ]
)

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

settings = GigaSettings()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    giga = GigaHelper(settings.chat_model, settings.embeddings)
    context.chat_data["giga"] = giga
    start_text = os.getenv("START_TEXT")
    await context.bot.send_message(chat_id=update.effective_chat.id, text=start_text)


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    giga = GigaHelper(settings.chat_model, settings.embeddings)
    context.chat_data["giga"] = giga
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Контекст сброшен.")


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _logger.info("Вопрос %s: %s", update.message.from_user.username, update.message.text)
    giga: GigaHelper = context.chat_data.get("giga") or await get_helper()
    attempt = 0
    result = None
    while not result and attempt < 10:
        try:
            result = await giga.aget_answer(update.message.text)
        except Exception as e:
            _logger.error(e)
            attempt = attempt + 1
            await sleep(1)

    context.chat_data["giga"] = giga
    result = result or (
        "Возникла тех. ошибка. "
        "Повторите запрос, пожалуйста."
    )
    if attempt > 0:
        result = "Простите, что заставил ждать. " + result

    _logger.info("Ответ %s: %s", update.message.from_user.username, result)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=result, disable_web_page_preview=False)


async def get_helper():
    return GigaHelper(settings.chat_model, settings.embeddings)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Извини, я не понимаю эту команду.\n"
             "Для сброса контекста используй команды /start или /clear"
    )


def get_app():
    application = (ApplicationBuilder()
                   .token(os.getenv("TELEGRAM_BOT_TOKEN"))
                   # .persistence(persistence=my_persistence)
                   .build()
                   )
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('clear', clear))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), answer))
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    return application


# my_persistence = PicklePersistence(
#     filepath=str(pathlib.Path(__file__).parent.parent.parent / "storage"),
#     on_flush=False,
# )