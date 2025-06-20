import logging
from functools import wraps
from telegram.ext import ConversationHandler

logger = logging.getLogger(__name__)

def handle_errors(error_message, return_state=None):
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            try:
                return await func(update, context, *args, **kwargs)
            except Exception as e:
                logger.error(f"Errore in {func.__name__}: {str(e)}", exc_info=True)
                if update.message:
                    await update.message.reply_text(error_message)
                elif update.callback_query:
                    await update.callback_query.message.reply_text(error_message)
                return return_state if return_state is not None else ConversationHandler.END
        return wrapper
    return decorator