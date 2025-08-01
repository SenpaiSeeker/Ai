import os
import re
import asyncio
from dotenv import load_dotenv

import pyrogram
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
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

db = app.ns.db(storage_type="local",)

chatbot = app.ns.gemini(api_key=GEMINI_API_KEY)


async def get_response_and_update_history(user_id: int, user_input: str) -> str:
    history = db.getVars(user_id, "GEMINI_HISTORY") or []
    
    chatbot.chat_history[user_id] = history
    
    def call_gemini_sync():
        return chatbot.send_chat_message(
            message=user_input, 
            user_id=user_id, 
            bot_name="GeminiBot"
        )

    response_text = await asyncio.to_thread(call_gemini_sync)
    
    updated_history = chatbot.chat_history.get(user_id, [])
    
    db.setVars(user_id, "GEMINI_HISTORY", updated_history)
    
    return response_text


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
    user_id = message.from_user.id
    db.removeVars(user_id, "GEMINI_HISTORY")
    if user_id in chatbot.chat_history:
        del chatbot.chat_history[user_id]
    await message.reply_text("✅ Riwayat percakapan Anda telah berhasil dihapus.")


@app.on_message(filters.text & filters.private)
async def handle_chat(client: Client, message: Message):
    user_id = message.from_user.id
    user_input = message.text
    processing_message = await message.reply_text("🤔 AI sedang berpikir...")
    try:
        response_text = await get_response_and_update_history(user_id, user_input)
        await processing_message.edit_text(response_text)
    except Exception as e:
        app.ns.log.error(f"Error saat memproses chat dari user {user_id}: {e}")
        await processing_message.edit_text("Maaf, terjadi kesalahan saat memproses permintaan Anda.")


@app.on_inline_query()
async def handle_inline_query(client: Client, inline_query: InlineQuery):
    query = inline_query.query.strip()
    if not query:
        return

    placeholder_text = f"🤔 **Prompt:**\n`{query}`\n\n💡 **Jawaban Gemini:**\n*Sedang memproses...*"
    
    results = [
        InlineQueryResultArticle(
            title="Tanya Gemini (Klik untuk Kirim)",
            description=f"Prompt: {query[:50]}...",
            input_message_content=InputTextMessageContent(placeholder_text),
            thumb_url="https://i.imgur.com/nwJdA52.png",
        )
    ]
    await inline_query.answer(results=results, cache_time=1)


@app.on_message(
    filters.text & 
    filters.me &
    filters.regex(r"^🤔 \*\*Prompt:\*\*\n`(.+?)`\n\n💡 \*\*Jawaban Gemini:\*\*\n\*Sedang memproses\.\.\.\*")
)
async def edit_inline_response(client: Client, message: Message):
    original_query = message.matches[0].group(1)
    
    try:
        inline_user_id = f"inline_{message.chat.id or 'unknown'}"
        def get_inline_response():
            return chatbot.send_chat_message(
                message=original_query,
                user_id=inline_user_id,
                bot_name="GeminiBot"
            )
        response_text = await asyncio.to_thread(get_inline_response)
        
        if inline_user_id in chatbot.chat_history:
            del chatbot.chat_history[inline_user_id]
        
        final_text = f"🤔 **Prompt:**\n`{original_query}`\n\n💡 **Jawaban Gemini:**\n{response_text}"
        
        await message.edit_text(final_text)

    except Exception as e:
        app.ns.log.error(f"Error saat edit inline response: {e}")
        await message.edit_text(
            f"🤔 **Prompt:**\n`{original_query}`\n\n"
            f"❌ **Error:**\nMaaf, terjadi kesalahan saat memproses permintaan ini."
        )

if __name__ == "__main__":
    print("Bot Gemini sedang berjalan...")
    app.run()
