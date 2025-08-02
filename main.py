import os
import uuid
import asyncio
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    InlineQueryHandler,
    ContextTypes,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError

import nsdev

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

chatbot = nsdev.ChatbotGemini(api_key=GEMINI_API_KEY)
log = nsdev.LoggerHandler()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"👋 Halo, {user.mention_html()}!\n\n"
        "Saya adalah bot AI Gemini yang bekerja via inline.\n\n"
        f"Ketik <code>@{context.bot.username} [pertanyaan]</code> di chat manapun untuk mendapatkan jawaban langsung."
    )

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query.query.strip()
    if not query:
        return

    result_id = str(uuid.uuid4())

    try:
        def get_response_sync():
            return chatbot.send_chat_message(
                message=query,
                user_id=f"inline_{update.inline_query.from_user.id}",
                bot_name="GeminiBot"
            )
        response_text = await asyncio.to_thread(get_response_sync)
        
        final_text = f"🤔 **Prompt:**\n`{query}`\n\n💡 **Jawaban Gemini:**\n{response_text}"
        
        keyboard = [
            [
                InlineKeyboardButton("✏️ Ubah & Tanya Lagi", switch_inline_query_current_chat=query),
                InlineKeyboardButton("💬 Tanya Baru", switch_inline_query_current_chat="")
            ]
        ]
        final_markup = InlineKeyboardMarkup(keyboard)

        final_result = [
            InlineQueryResultArticle(
                id=result_id,
                title="Jawaban dari Gemini AI",
                description=response_text.replace("\n", " ")[:60],
                input_message_content=InputTextMessageContent(
                    final_text,
                    parse_mode=ParseMode.MARKDOWN
                ),
                reply_markup=final_markup,
                thumbnail_url="https://files.catbox.moe/ozzvtz.jpg",
                thumbnail_width=64,
                thumbnail_height=64,
            )
        ]
        await update.inline_query.answer(final_result, cache_time=1)

    except TelegramError as e:
        log.warning(f"TelegramError saat menjawab inline query: {e}")
    except Exception as e:
        log.error(f"Error pada handler inline_query: {e}")
        try:
            error_result = [
                InlineQueryResultArticle(
                    id=result_id,
                    title="❌ Terjadi Kesalahan",
                    description="Tidak dapat memproses permintaan Anda.",
                    input_message_content=InputTextMessageContent(f"❌ Gagal memproses prompt: `{query}`")
                )
            ]
            await update.inline_query.answer(error_result, cache_time=1)
        except Exception:
            pass

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(InlineQueryHandler(inline_query))

    log.print(f"{log.GREEN}Bot Gemini (python-telegram-bot) sedang berjalan...")
    application.run_polling()


if __name__ == "__main__":
    main()
