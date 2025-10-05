import logging
import os
import pathlib
from asyncio import sleep
import datetime

from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, JobQueue, CallbackQueryHandler

from giga_helper.helper import GigaHelper
from giga_helper.settings import GigaSettings

from . import statistic
from . import helpers
from . import intent

from .helpers import ADMIN_ID

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


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    if update.effective_user.id != ADMIN_ID:
        _logger.warning(f"Попытка несанкционированного доступа к статистике от пользователя {update.effective_user.id}")
        return
    stats_message = statistic.get_stats_message(context)
    
    await context.bot.send_message(chat_id=ADMIN_ID, text=stats_message)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    giga = GigaHelper(settings.chat_model, settings.embeddings)
    context.chat_data["giga"] = giga
    start_text = os.getenv("START_TEXT")
    await context.bot.send_message(chat_id=update.effective_chat.id, text=start_text)


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    giga = GigaHelper(settings.chat_model, settings.embeddings)
    context.chat_data["giga"] = giga
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Контекст сброшен.")

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    giga = GigaHelper(settings.chat_model, settings.embeddings)
    context.chat_data["giga"] = giga
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Обратная связь @Sedoy_av")


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )

    statistic.update_stats(update, context)
    await helpers.forward_to_admin(update, context)

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

    keyboard = [
        [
            InlineKeyboardButton("👍 Полезно", callback_data="feedback_good"),
            InlineKeyboardButton("👎 Не полезно", callback_data="feedback_bad"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=result, disable_web_page_preview=False, reply_markup=reply_markup)

async def feedback_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    query = update.callback_query
    
    
    await query.answer()

    
    feedback_data = query.data
    user = query.from_user

    
    _logger.info(
        f"Получена обратная связь от {user.username} (ID: {user.id}): "
        f"'{feedback_data}' на ответ: '{query.message.text[:50]}...'"
    )

    
    await query.edit_message_reply_markup(reply_markup=None)

    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Спасибо за ваш отзыв!",
        
        reply_to_message_id=query.message.message_id
    )


async def get_helper():
    return GigaHelper(settings.chat_model, settings.embeddings)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Извини, я не понимаю эту команду.\n"
             "Для сброса контекста используй команды /start или /clear"
    )


def get_app():
    
    job_queue = JobQueue()

    application = (ApplicationBuilder()
                   .token(os.getenv("TELEGRAM_BOT_TOKEN"))
                   .job_queue(job_queue)
                   .read_timeout(30)
                   .write_timeout(30)
                   .build()
                   )

    
    job_queue.run_daily(
        statistic.reset_stats,
        time=datetime.time(hour=0, minute=0, second=0, tzinfo=ZoneInfo("Europe/Moscow")),
        name="daily_stats_reset"
    )
    
    sberdocs_pattern = r'(?i).*(сбердокс|sberdocs|инструкция).*'
    trip_pattern = r'(?i).*(командировк|инструкция по командировкам).*'
    kprib_pattern = r'(?i).*кприб.*'
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('clear', clear))
    application.add_handler(CommandHandler('feedback', feedback))
    application.add_handler(CommandHandler('stats', stats_command))
    
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(sberdocs_pattern), intent.handle_sberdocs_request))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(trip_pattern), intent.handle_trip_request))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(kprib_pattern), intent.handle_kprib_request))

    application.add_handler(CallbackQueryHandler(feedback_button_handler))
    
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), answer))
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    return application

# my_persistence = PicklePersistence(
#     filepath=str(pathlib.Path(__file__).parent.parent.parent / "storage"),
#     on_flush=False,
# )