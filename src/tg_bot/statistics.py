import logging

from telegram import Update
from telegram.ext import ContextTypes

_logger = logging.getLogger(__name__)


def update_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    stats = context.bot_data.setdefault('daily_stats', {'total_messages': 0, 'unique_users': set()})

    stats['total_messages'] += 1
    stats['unique_users'].add(user_id)
    _logger.info(
        f"Статистика обновлена. Всего сообщений: {stats['total_messages']}, уникальных пользователей: {len(stats['unique_users'])}")


def get_stats_message(context: ContextTypes.DEFAULT_TYPE) -> str:
    stats = context.bot_data.get('daily_stats', {'total_messages': 0, 'unique_users': set()})

    total_messages = stats['total_messages']
    unique_users = len(stats['unique_users'])

    message = (
        f"📊 Статистика за сегодня:\n\n"
        f"Всего вопросов: {total_messages}\n"
        f"Уникальных пользователей: {unique_users}"
    )
    return message


async def reset_stats(context: ContextTypes.DEFAULT_TYPE):
    context.bot_data['daily_stats'] = {'total_messages': 0, 'unique_users': set()}
    _logger.info("Суточная статистика сброшена.")
