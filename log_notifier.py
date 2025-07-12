from fastapi import Request
from telegram import Bot
import os
import logging
from fastapi.responses import JSONResponse
from logging.handlers import RotatingFileHandler

LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "errors.log")
rotating_file_handler = RotatingFileHandler(
    LOG_FILE_PATH, maxBytes=5 * 1024 * 1024, backupCount=10, encoding="utf-8"
)

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        rotating_file_handler,
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('Gamemoneta.site')

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TOKEN)
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
THREAD_ID = os.getenv("TELEGRAM_THREAD_ID", "")


async def exception_handler(request: Request, exc: Exception):
    error_message = (
        f"*Ошибка*: `{str(exc)}`\n"
        f"*Путь*: `{request.url.path}`\n"
        f"*Метод*: _{request.method}_\n"
    )

    logger.error(error_message)

    try:
        await bot.send_message(chat_id=CHAT_ID, message_thread_id=THREAD_ID, text=error_message,
                               parse_mode="Markdown")
    except Exception as telegram_error:
        logger.error(f"Failed to send error notification to Telegram: {telegram_error}")

    return JSONResponse(status_code=500, content={"detail": "An internal server error occurred."})
