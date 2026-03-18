"""
Telegram-бот: пересылка сообщений нескольким администраторам с возможностью ответа.

Установка зависимостей:
    pip install python-telegram-bot==20.7

Запуск:
    python bot.py

Настройка:
    Замените BOT_TOKEN и ADMIN_IDS своими значениями.
    Узнать свой chat_id можно написав боту @userinfobot в Telegram.
"""

import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ─── Настройки ───────────────────────────────────────────────────────────────

BOT_TOKEN = "8618643151:AAHE3F8A1xTR1DykhlsrB_LnLe9D9B-JRp4"   # токен от @BotFather

# Список chat_id всех администраторов
ADMIN_IDS: list[int] = [
    8525396766,   # Админ 2
    6127557724,   # Админ 3
]

# ─── Логирование ─────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Хранилище соответствий ──────────────────────────────────────────────────
# (admin_chat_id, forwarded_msg_id) → original_user_chat_id
# Каждый админ получает своё сообщение со своим message_id, поэтому
# ключ — пара (chat_id админа, id пересланного сообщения).

forwarded_to_user: dict[tuple[int, int], int] = {}


# ─── Вспомогательные функции ─────────────────────────────────────────────────

def is_admin(chat_id: int) -> bool:
    return chat_id in ADMIN_IDS


# ─── Обработчики ─────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приветствие."""
    if is_admin(update.effective_chat.id):
        await update.message.reply_text(
            "👋 Привет, администратор!\n"
            "Сообщения от пользователей будут приходить сюда.\n"
            "Чтобы ответить — нажмите Reply на нужное сообщение."
        )
    else:
        await update.message.reply_text(
            "Уважаемый пользователь, отправьте любое сообщение и мы вам ответим."
        )


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Получаем сообщение от пользователя → пересылаем ВСЕМ администраторам.
    Сохраняем связь для каждого пересланного сообщения отдельно.
    """
    user    = update.effective_user
    chat_id = update.effective_chat.id
    text    = update.message.text or update.message.caption or "[медиа без текста]"

    username_part = f"@{user.username}" if user.username else f"id={user.id}"
    header = (
        f"✉️ Новое сообщение\n"
        f"От: {user.full_name} ({username_part})\n"
        f"chat_id: {chat_id}\n"
        f"{'─' * 30}\n"
        f"{text}"
    )

    sent_count = 0
    for admin_id in ADMIN_IDS:
        try:
            sent = await context.bot.send_message(chat_id=admin_id, text=header)
            forwarded_to_user[(admin_id, sent.message_id)] = chat_id
            sent_count += 1
        except Exception as e:
            logger.warning("Не удалось отправить сообщение админу %s: %s", admin_id, e)

    if sent_count:
        await update.message.reply_text("✅ Сообщение отправлено. Ожидайте ответа.")
    else:
        await update.message.reply_text("⚠️ Не удалось доставить сообщение. Попробуйте позже.")

    logger.info(
        "Переслано от %s (chat_id=%s) → %d/%d админам",
        user.full_name, chat_id, sent_count, len(ADMIN_IDS),
    )


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Когда любой из администраторов делает Reply на пересланное сообщение —
    отправляем его текст обратно пользователю.
    """
    admin_chat_id = update.effective_chat.id
    reply_to      = update.message.reply_to_message

    if reply_to is None:
        await update.message.reply_text(
            "ℹ️ Чтобы ответить пользователю, сделайте Reply (ответ) на пересланное сообщение."
        )
        return

    key          = (admin_chat_id, reply_to.message_id)
    user_chat_id = forwarded_to_user.get(key)

    if user_chat_id is None:
        await update.message.reply_text(
            "⚠️ Не удалось определить получателя. "
            "Убедитесь, что отвечаете на сообщение, пришедшее через бота."
        )
        return

    admin_text = update.message.text or "[без текста]"

    admin_name = "Anonim \"Hack#r\""

    await context.bot.send_message(
        chat_id=user_chat_id,
        text=f"📩 Ответ от администратора ({admin_name}):\n\n{admin_text}",
    )

    await update.message.reply_text("✅ Ответ доставлен пользователю.")
    logger.info(
        "Админ %s (id=%s) ответил пользователю chat_id=%s",
        admin_name, admin_chat_id, user_chat_id,
    )


# ─── Точка входа ─────────────────────────────────────────────────────────────

def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            filters.Chat(ADMIN_IDS) & filters.TEXT & ~filters.COMMAND,
            handle_admin_reply,
        )
    )

    app.add_handler(
        MessageHandler(
            ~filters.Chat(ADMIN_IDS) & (filters.TEXT | filters.CAPTION),
            handle_user_message,
        )
    )

    logger.info("Бот запущен. Администраторов: %d. Ожидание сообщений...", len(ADMIN_IDS))
    app.run_polling()


if __name__ == "__main__":
    main()
