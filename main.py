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

# --- FUNGSI PENTING UNTUK MEMBERSIHKAN TEKS DARI AI ---
def sanitize_markdown(text: str) -> str:
    """Memperbaiki Markdown yang rusak dari output AI."""
    # Karakter yang sering menyebabkan masalah jika tidak ditutup
    markers = ['*', '_', '`']
    for marker in markers:
        # Jika jumlah marker ganjil, tambahkan satu di akhir untuk menutupnya
        if text.count(marker) % 2 != 0:
            text += marker
            
    # Membersihkan blok kode yang tidak ditutup
    if text.count('```') % 2 != 0:
        text += '\n```'
        
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"👋 Halo, {user.mention_html()}!\n\n"
        "Saya adalah bot AI Gemini yang bekerja via inline.\n\n"
        f"Ketik <code>@{context.bot.username} [pertanyaan]</code> di chat manapun untuk mendapatkan jawaban langsung."
    )

async def get_ai_answer_and_update(
    update: Update, context: ContextTypes.DEFAULT_TYPE, query: str, result_id: str
) -> None:
    """Tugas background untuk mengambil jawaban AI dan memperbarui hasil inline."""
    try:
        def get_response_sync():
            return chatbot.send_chat_message(
                message=query,
                user_id=f"inline_{update.inline_query.from_user.id}",
                bot_name="GeminiBot"
            )
        response_text = await asyncio.to_thread(get_response_sync)
        
        # Gunakan fungsi sanitasi pada output AI
        sanitized_response = sanitize_markdown(response_text)
        
        final_text = f"🤔 **Prompt:**\n`{query}`\n\n💡 **Jawaban Gemini:**\n{sanitized_response}"
        
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
                description=sanitized_response.replace("\n", " ")[:60],
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
        # Ini normal jika pengguna sudah menutup menu inline
        if "Query is too old" in str(e):
            log.warning(f"Query ID expired, update untuk '{query}' dibatalkan.")
        else:
            log.error(f"TelegramError pada background task: {e}")
    except Exception as e:
        log.error(f"Error pada background task inline: {e}")
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

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menangani permintaan inline, mengirim placeholder, dan memproses di background."""
    query = update.inline_query.query.strip()
    if not query:
        return

    result_id = str(uuid.uuid4())

    placeholder_result = [
        InlineQueryResultArticle(
            id=result_id,
            title="⏳ Memproses...",
            description="AI sedang berpikir, harap tunggu sebentar.",
            input_message_content=InputTextMessageContent("Sedang menunggu jawaban dari AI...")
        )
    ]
    # Kirim placeholder SEGERA untuk menghindari timeout
    await update.inline_query.answer(placeholder_result, cache_time=1)

    # Jalankan tugas yang sebenarnya di background
    asyncio.create_task(
        get_ai_answer_and_update(update, context, query, result_id)
    )

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(InlineQueryHandler(inline_query))

    log.print(f"{log.GREEN}Bot Gemini (python-telegram-bot) sedang berjalan...")
    application.run_polling()


if __name__ == "__main__":
    main()
