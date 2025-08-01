import os
import asyncio
from dotenv import load_dotenv

import pyrogram
from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

import nsdev

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

app = Client(
    "gemini_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

db = app.ns.db(storage_type="local")

chatbot = app.ns.gemini(api_key=GEMINI_API_KEY)


@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text(
        f"👋 Halo, {message.from_user.first_name}!\n\n"
        "Saya adalah bot AI yang didukung oleh Google Gemini.\n\n"
        "🔹 **Mode Chat**: Kirim saya pesan apa saja di sini, dan saya akan mengingat percakapan kita.\n"
        f"🔹 **Mode Inline**: Ketik `@{(await client.get_me()).username} <pertanyaan>` di chat manapun untuk mendapatkan jawaban cepat.\n"
        "🔹 **Hapus Riwayat**: Gunakan perintah /clear untuk menghapus riwayat percakapan kita."
    )


@app.on_message(filters.command("clear") & filters.private)
async def clear_command(client: Client, message: Message):
    """Handler untuk perintah /clear"""
    user_id = message.from_user.id
    
    db.removeVars(user_id, "GEMINI_HISTORY")
    
    if user_id in chatbot.chat_history:
        del chatbot.chat_history[user_id]
        
    await message.reply_text("✅ Riwayat percakapan Anda telah berhasil dihapus.")


@app.on_message(filters.text & filters.private & ~filters.command(None))
async def handle_chat(client: Client, message: Message):
    user_id = message.from_user.id
    user_input = message.text
    
    processing_message = await message.reply_text("🤔 AI sedang berpikir...")

    try:
        history = db.getVars(user_id, "GEMINI_HISTORY") or []
        
        chatbot.chat_history[user_id] = history
        
        def get_gemini_response():
            return chatbot.send_chat_message(
                message=user_input, 
                user_id=user_id, 
                bot_name="GeminiBot"
            )

        response_text = await asyncio.to_thread(get_gemini_response)

        updated_history = chatbot.chat_history[user_id]
        
        db.setVars(user_id, "GEMINI_HISTORY", updated_history)

        await processing_message.edit_text(response_text)

    except Exception as e:
        app.ns.log.error(f"Error saat memproses chat dari user {user_id}: {e}")
        await processing_message.edit_text(
            "Maaf, terjadi kesalahan saat memproses permintaan Anda. Coba lagi nanti."
        )


@app.on_inline_query()
async def handle_inline_query(client: Client, inline_query: InlineQuery):
    query = inline_query.query.strip()

    if not query:
        return

    try:
        inline_user_id = f"inline_{inline_query.from_user.id}"
        
        def get_inline_response():
            return chatbot.send_chat_message(
                message=query,
                user_id=inline_user_id,
                bot_name="GeminiBot"
            )

        response_text = await asyncio.to_thread(get_inline_response)
        
        if inline_user_id in chatbot.chat_history:
            del chatbot.chat_history[inline_user_id]
        
        edit_query_button = InlineKeyboardButton(
            text="✏️ Ubah & Tanya Lagi",
            switch_inline_query_current_chat=query
        )
        
        new_query_button = InlineKeyboardButton(
            text="💬 Tanya Baru",
            switch_inline_query_current_chat=""
        )
        
        reply_markup = InlineKeyboardMarkup(
            [
                [edit_query_button, new_query_button]
            ]
        )

        results = [
            InlineQueryResultArticle(
                title="Kirim Jawaban dari Gemini AI",
                description=f"Prompt: {query[:50]}...",
                input_message_content=InputTextMessageContent(
                    f"🤔 **Prompt:**\n`{query}`\n\n💡 **Jawaban Gemini:**\n{response_text}"
                ),
                reply_markup=reply_markup
            )
        ]
        
        await inline_query.answer(results=results, cache_time=1)

    except Exception as e:
        app.ns.log.error(f"Error pada inline query: {e}")
        await inline_query.answer(
            results=[
                InlineQueryResultArticle(
                    title="Terjadi Kesalahan",
                    description=str(e),
                    input_message_content=InputTextMessageContent(
                        "Maaf, terjadi kesalahan saat memproses permintaan Anda."
                    )
                )
            ],
            cache_time=1
        )

if __name__ == "__main__":
    print("Bot Gemini sedang berjalan...")
    app.run()
