import logging
import os
import pathlib
import uuid
from asyncio import sleep

from telegram import Update
from telegram.error import Forbidden
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from rag_helper.helper import RagHelper
from rag_helper.llms import ModelsStorage
from tg_bot import INSTRUCTIONS_PATH, USER_TMP_STORAGE_PATH

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

_MODELS_STORAGE = ModelsStorage()
_HELPER = "helper"

ADMIN_ID = 6115888642


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data[_HELPER] = create_helper()
    start_text = os.getenv("START_TEXT")
    await context.bot.send_message(chat_id=update.effective_chat.id, text=start_text)


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data[_HELPER] = create_helper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Контекст сброшен.")


async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Обратная связь @Sedoy_av")


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # await forward_to_admin(update, context)

    _logger.info("Вопрос %s: %s", update.message.from_user.username, update.message.text)
    result = await answer_by_helper(update, context)

    _logger.info("Ответ %s: %s", update.message.from_user.username, result)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=result, disable_web_page_preview=False)


async def answer_by_helper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    helper: RagHelper = context.chat_data.get(_HELPER) or create_helper()
    attempt = 0
    result: str | None = None

    attachment_path = None
    if update.message.document or update.message.photo:
        file_to_download = await (update.message.document or update.message.photo[-1]).get_file()

        file_name_with_extension = os.path.basename(file_to_download.file_path)
        _, file_extension = os.path.splitext(file_name_with_extension)
        attachment_path = await file_to_download.download_to_drive(
            custom_path=USER_TMP_STORAGE_PATH / f"{str(uuid.uuid4())}.{file_extension}")

    while not result and attempt < 5:
        try:
            result = await helper.aget_answer(update.message.text or update.message.caption, attachment=attachment_path)
        except Exception as e:
            _logger.exception(e)
            attempt = attempt + 1
            await sleep(1)

    if attachment_path:
        os.remove(attachment_path)
    context.chat_data[_HELPER] = helper
    result = result or (
        "Возникла тех. ошибка. "
        "Повторите запрос, пожалуйста."
    )
    if attempt > 0:
        result = f"Простите, что заставил ждать.\n{result}"
    return result


async def answer_to_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = await answer_by_helper(update, context)
    # await context.bot.send_photo(chat_id=update.effective_chat.id, photo=buffer)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=answer)


def create_helper():
    return RagHelper(_MODELS_STORAGE.chat_model, _MODELS_STORAGE.embeddings)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Извини, я не понимаю эту команду.\n"
             "Для сброса контекста используй команды /start или /clear."
    )


# --- ПЕРЕМЕЩЕННЫЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

async def _send_document(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: pathlib.Path,
                         user_filename: str, log_intent: str, caption: str = None):
    _logger.info("Запрос на документ по интенту '%s' от %s", log_intent, update.message.from_user.username)

    try:

        if not file_path.is_file():
            _logger.error("Файл не найден по пути: %s", file_path)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Извините, не могу найти файл '{user_filename}'. Обратитесь к администратору."
            )
            return

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(file_path, 'rb'),
            filename=user_filename,
            caption=caption
        )
        _logger.info("Документ '%s' успешно отправлен пользователю %s", user_filename,
                     update.message.from_user.username)

    except Exception as e:
        _logger.error("Критическая ошибка при отправке документа '%s': %s", user_filename, e)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла непредвиденная ошибка при отправке файла."
        )


async def _send_video(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: pathlib.Path, user_filename: str,
                      log_intent: str, caption: str = None):
    _logger.info("Запрос на видео по интенту '%s' от %s", log_intent, update.message.from_user.username)

    try:

        if not file_path.is_file():
            _logger.error("Файл не найден по пути: %s", file_path)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Извините, не могу найти файл '{user_filename}'. Обратитесь к администратору."
            )
            return

        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=open(file_path, 'rb'),
            filename=user_filename,
            caption=caption
        )
        _logger.info("Видео '%s' успешно отправлено пользователю %s", user_filename, update.message.from_user.username)

    except Exception as e:
        _logger.error("Критическая ошибка при отправке видео '%s': %s", user_filename, e)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла непредвиденная ошибка при отправке файла."
        )


# --- ОБРАБОТЧИКИ ИНТЕНТОВ ---

async def handle_sberdocs_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await forward_to_admin(update, context)
    file_path = INSTRUCTIONS_PATH / "SberDocs.docx"
    await _send_document(
        update,
        context,
        file_path=file_path,
        user_filename="Инструкция_SberDocs.docx",
        log_intent="СберДокс",
        caption="Ознакомьтесь с подробной инструкцией открыв файл"
    )


async def handle_trip_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await forward_to_admin(update, context)
    file_path = INSTRUCTIONS_PATH / "Инструкция по командировкам.docx"
    await _send_document(
        update,
        context,
        file_path=file_path,
        user_filename="Инструкция по командировкам.docx",
        log_intent="Командировки",
        caption="Ознакомьтесь с подробной инструкцией открыв файл"
    )


async def handle_kprib_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await forward_to_admin(update, context)
    file_path = INSTRUCTIONS_PATH / "Барабан.mp4"
    await _send_video(
        update,
        context,
        file_path=file_path,
        user_filename="Барабан.mp4",
        log_intent="кприб",
        caption="крутите барабан"
    )


async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.message.from_user
        user_info_parts = []
        if user.first_name:
            user_info_parts.append(user.first_name)
        if user.last_name:
            user_info_parts.append(user.last_name)
        if user.username:
            user_info_parts.append(f"(@{user.username})")

        user_info = " ".join(user_info_parts) if user_info_parts else f"ID: {user.id}"

        _logger.info(f"Пересылка сообщения от {user_info} администратору (ID: {ADMIN_ID})")

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"Получено новое сообщение от пользователя: {user_info}"
        )

        await context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Forbidden:
        _logger.error(f"Не удалось отправить сообщение администратору (ID: {ADMIN_ID}). "
                      f"Возможно, бот заблокирован администратором.")
    except Exception as e:
        _logger.error(f"Непредвиденная ошибка при пересылке сообщения администратору: {e}")


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
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(sberdocs_pattern), handle_sberdocs_request))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(trip_pattern), handle_trip_request))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(kprib_pattern), handle_kprib_request))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), answer))
    application.add_handler(MessageHandler(filters.PHOTO, answer_to_image))
    application.add_handler(MessageHandler(filters.Document.IMAGE, answer_to_image))
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    return application

# my_persistence = PicklePersistence(
#     filepath=str(pathlib.Path(__file__).parent.parent.parent / "storage"),
#     on_flush=False,
# )
