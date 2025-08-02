import os
import uuid  # Pastikan untuk mengimpor ini
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
from pyrogram.errors import QueryIdInvalid

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
log = app.ns.log()


@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text(
        f"👋 Halo, {message.from_user.first_name}!\n\n"
        "Saya adalah bot AI Gemini yang bekerja via inline.\n\n"
        f"Ketik `@{(await client.get_me()).username} [pertanyaan]` di chat manapun untuk mendapatkan jawaban langsung."
    )


@app.on_inline_query()
async def handle_inline_query(client: Client, inline_query: InlineQuery):
    query = inline_query.query.strip()
    if not query:
        return

    result_id = uuid.uuid4().hex

    async def process_and_update():
        try:
            def get_response_sync():
                return chatbot.send_chat_message(
                    message=query,
                    user_id=f"inline_{inline_query.from_user.id}",
                    bot_name="GeminiBot"
                )
            response_text = await asyncio.to_thread(get_response_sync)
            
            final_text = f"🤔 **Prompt:**\n`{query}`\n\n💡 **Jawaban Gemini:**\n{response_text}"
            
            buttons_data = [
                {"text": "✏️ Ubah & Tanya Lagi", "switch_inline_query_current_chat": query},
                {"text": "💬 Tanya Baru", "switch_inline_query_current_chat": ""}
            ]
            final_markup = client.ns.button.build_button_grid(buttons=buttons_data, row_width=2)

            final_result = [
                InlineQueryResultArticle(
                    id=result_id,
                    title="Jawaban dari Gemini AI",
                    description=response_text.replace("\n", " ")[:60],
                    input_message_content=InputTextMessageContent(final_text),
                    thumb_url="https://files.catbox.moe/ozzvtz.jpg",
                    reply_markup=final_markup,
                )
            ]
            
            await inline_query.answer(results=final_result, cache_time=1)
        
        except QueryIdInvalid:
            log.warning(f"Query ID {inline_query.id} expired, update dibatalkan.")
        except Exception as e:
            log.error(f"Error pada proses background inline query: {e}")

    asyncio.create_task(process_and_update())

    placeholder_result = [
        InlineQueryResultArticle(
            id=result_id,
            title="⏳ Memproses...",
            description="AI sedang berpikir, harap tunggu sebentar.",
            input_message_content=InputTextMessageContent("Sedang menunggu jawaban dari AI...")
        )
    ]
    
    try:
        await inline_query.answer(results=placeholder_result, cache_time=1, is_personal=True)
    except QueryIdInvalid:
        pass


if __name__ == "__main__":
    log.print(f"{log.GREEN}Bot Gemini sedang berjalan...")
    app.run()
