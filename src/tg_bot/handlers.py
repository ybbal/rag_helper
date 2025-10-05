import logging
import os
import uuid
from asyncio import sleep

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from rag_helper.helper import RagHelper
from rag_helper.llms import ModelsStorage
from rag_helper.models import RagHelperAnswer
from tg_bot import USER_TMP_STORAGE_PATH
from tg_bot.helpers import forward_to_admin
from tg_bot.statistics import update_stats

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

_MODELS_STORAGE = ModelsStorage()
_HELPER = "helper"

_ADMIN_ID = 6115888642


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data[_HELPER] = create_helper()
    start_text = os.getenv("START_TEXT")
    await context.bot.send_message(chat_id=update.effective_chat.id, text=start_text)


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data[_HELPER] = create_helper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Контекст сброшен.")


async def answer_by_helper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    update_stats(update, context)
    await forward_to_admin(update, context)

    _logger.info("Вопрос %s:\n%s", update.message.from_user.username, update.message.text or update.message.caption)

    helper: RagHelper = context.chat_data.get(_HELPER) or create_helper()
    attempt = 0
    result: RagHelperAnswer | None = None

    attachment_path = None
    if update.message.document or update.message.photo:
        file_to_download = await (update.message.document or update.message.photo[-1]).get_file()

        file_name_with_extension = os.path.basename(file_to_download.file_path)
        _, file_extension = os.path.splitext(file_name_with_extension)
        attachment_path = await file_to_download.download_to_drive(
            custom_path=USER_TMP_STORAGE_PATH / f"{str(uuid.uuid4())}.{file_extension}")
        attachment_path = str(attachment_path)

    while not result and attempt < 5:
        try:
            result = await helper.aget_answer(update.message.text or update.message.caption,
                                              attachment=attachment_path)
        except Exception as e:
            _logger.exception(e)
            attempt = attempt + 1
            await sleep(1)

    if attachment_path:
        os.remove(attachment_path)
    context.chat_data[_HELPER] = helper
    result = result or RagHelperAnswer(
        text_message="Возникла тех. ошибка. "
                     "Повторите запрос, пожалуйста."

    )
    if attempt > 0:
        result.text_message = f"Простите, что заставил ждать.\n{result.text_message}"

    _logger.info("Ответ %s:\n%s", update.message.from_user.username, result.text_message)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=result.text_message,
        disable_web_page_preview=False,
        reply_markup=get_reply_markup(result)
    )
    if result.attachment_paths:
        for path in result.attachment_paths:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=path)
    return


def get_reply_markup(result: RagHelperAnswer) -> InlineKeyboardMarkup | None:
    if not result.need_feedback:
        return None
    keyboard = [
        [
            InlineKeyboardButton("👍 Полезно", callback_data="feedback_good"),
            InlineKeyboardButton("👎 Не полезно", callback_data="feedback_bad"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def create_helper():
    return RagHelper(_MODELS_STORAGE.chat_model, _MODELS_STORAGE.embeddings)


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Обратная связь @Sedoy_av")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Извини, я не понимаю эту команду.\n"
             "Для сброса контекста используй команды /start или /clear."
    )


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


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass
    # if update.effective_user.id != _ADMIN_ID:
    #     _logger.warning(f"Попытка несанкционированного доступа к статистике от пользователя {update.effective_user.id}")
    #     return
    # stats_message = get_stats_message(context)
    #
    # await context.bot.send_message(chat_id=_ADMIN_ID, text=stats_message)
