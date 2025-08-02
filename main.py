import os
import asyncio
from dotenv import load_dotenv

import pyrogram
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    ChosenInlineResult,
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
        "Saya adalah bot AI yang didukung oleh Google Gemini.\n\n"
        f"Saya sekarang bekerja sepenuhnya otomatis melalui mode inline. "
        f"Ketik `@{(await client.get_me()).username} [pertanyaan]` di chat manapun dan pilih hasilnya."
    )


@app.on_inline_query()
async def handle_inline_query(client: Client, inline_query: InlineQuery):
    query = inline_query.query.strip()
    if not query:
        return

    placeholder_text = f"🤔 **Prompt:**\n`{query}`\n\n⏳ __AI sedang memproses, harap tunggu...__"
    
    results = [
        InlineQueryResultArticle(
            title="Kirim Permintaan ke Gemini AI",
            description=f"Prompt: {query[:40]}...",
            input_message_content=InputTextMessageContent(placeholder_text),
            thumb_url="https://files.catbox.moe/ozzvtz.jpg",
            id=str(hash(query))
        )
    ]
    try:
        await inline_query.answer(results=results, cache_time=1)
    except QueryIdInvalid:
        pass


@app.on_chosen_inline_result()
async def auto_edit_from_chosen(client: Client, chosen_inline_result: ChosenInlineResult):
    query = chosen_inline_result.query
    inline_message_id = chosen_inline_result.inline_message_id

    try:
        def get_response():
            return chatbot.send_chat_message(
                message=query, 
                user_id=f"chosen_{chosen_inline_result.from_user.id}", 
                bot_name="GeminiBot"
            )
        response_text = await asyncio.to_thread(get_response)

        final_text = f"🤔 **Prompt:**\n`{query}`\n\n💡 **Jawaban Gemini:**\n{response_text}"
        
        await client.edit_message_text(
            inline_message_id=inline_message_id,
            text=final_text
        )

    except Exception as e:
        log.error(f"Gagal memproses ChosenInlineResult: {e}")
        try:
            await client.edit_message_text(
                inline_message_id=inline_message_id,
                text=f"❌ **Terjadi Kesalahan**\n\nMaaf, saya tidak dapat memproses permintaan untuk prompt:\n`{query}`"
            )
        except Exception as edit_error:
            log.error(f"Gagal mengirim pesan error ke inline_message_id: {edit_error}")


if __name__ == "__main__":
    log.info("Bot Gemini (Auto-Edit Inline) sedang berjalan...")
    app.run()
