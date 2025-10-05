import logging
import pathlib
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import Forbidden

_logger = logging.getLogger(__name__)


ADMIN_ID = 6115888642

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

async def send_document(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: pathlib.Path, user_filename: str, log_intent: str, caption: str = None):
    
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
        _logger.info("Документ '%s' успешно отправлен пользователю %s", user_filename, update.message.from_user.username)

    except Exception as e:
        _logger.error("Критическая ошибка при отправке документа '%s': %s", user_filename, e)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Произошла непредвиденная ошибка при отправке файла."
        )

async def send_video(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: pathlib.Path, user_filename: str, log_intent: str, caption: str = None):
    
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