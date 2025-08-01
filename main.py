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

chatbot = app.ns.gemini(api_key=GEMINI_API_KEY)


@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text(
        f"👋 Halo, saya adalah bot AI Gemini.\n\n"
        f"Saya hanya bekerja dalam mode inline. Coba ketik `@{(await client.get_me()).username} <pertanyaan>` di chat manapun."
    )


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
            input_message_content=InputTextMessageContent(
                message_text=placeholder_text,
                parse_mode=pyrogram.enums.ParseMode.MARKDOWN
            ),
            thumb_url="https://i.imgur.com/nwJdA52.png",
        )
    ]
    await inline_query.answer(results=results, cache_time=1)


@app.on_message(
    filters.via_bot &
    filters.text &
    filters.regex(r"^🤔 Prompt:\n(.+?)\n\n💡 Jawaban Gemini:\nSedang memproses\.\.\.")
)
async def edit_inline_response(client: Client, message: Message):
    if not message.via_bot or message.via_bot.id != client.me.id:
        return

    original_query = message.matches[0].group(1)
    
    try:
        def get_inline_response():
            return chatbot.send_chat_message(
                message=original_query,
                user_id=f"inline_{message.from_user.id}",
                bot_name="GeminiBot"
            )
        response_text = await asyncio.to_thread(get_inline_response)
        
        final_text = f"🤔 **Prompt:**\n`{original_query}`\n\n💡 **Jawaban Gemini:**\n{response_text}"
        
        await message.edit_text(
            text=final_text,
            parse_mode=pyrogram.enums.ParseMode.MARKDOWN
        )

    except Exception as e:
        app.ns.log.error(f"Error saat edit inline response: {e}")
        await message.edit_text(
            f"🤔 **Prompt:**\n`{original_query}`\n\n"
            f"❌ **Error:**\nMaaf, terjadi kesalahan saat memproses permintaan ini."
        )

if __name__ == "__main__":
    print("Bot Gemini (Inline-Only) sedang berjalan...")
    app.run()
