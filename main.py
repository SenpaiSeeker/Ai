import os
import uuid
import asyncio
from dotenv import load_dotenv

import pyrogram
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    ChosenInlineResult,
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

db = app.ns.db(storage_type="local")
chatbot = app.ns.gemini(api_key=GEMINI_API_KEY)
log = app.ns.log

async def process_and_cache_gemini(user_id: int, query: str):
    log.info(f"Memulai pre-fetching untuk user {user_id} dengan query: {query[:30]}...")
    try:
        def get_response_sync():
            return chatbot.send_chat_message(
                message=query, user_id=f"prefetch_{user_id}", bot_name="GeminiBot"
            )
        response_text = await asyncio.to_thread(get_response_sync)
        
        query_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, query).hex)
        
        db.setVars(user_id, query_id, response_text, var_key="CACHED_RESULTS")
        log.info(f"Pre-fetching berhasil untuk user {user_id}, query_id: {query_id}")
    except Exception as e:
        log.error(f"Gagal pre-fetching untuk user {user_id}: {e}")

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text(
        f"👋 Halo, {message.from_user.first_name}!\n\n"
        "Saya adalah bot AI yang didukung oleh Google Gemini.\n\n"
        f"Gunakan saya melalui mode inline (`@{(await client.get_me()).username} [pertanyaan]`) untuk memulai."
    )

@app.on_inline_query()
async def handle_inline_query(client: Client, inline_query: InlineQuery):
    query = inline_query.query.strip()
    if not query:
        return

    query_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, query).hex)
    db.setVars(inline_query.from_user.id, query_id, query, var_key="TEMP_PROMPTS")
    
    callback_data = f"get_gem:{query_id}"
    placeholder_text = f"🤔 **Prompt:**\n`{query}`\n\n__Klik tombol di bawah untuk memproses...__"
    button_data = [{"text": "⏳ Proses Permintaan AI", "callback_data": callback_data}]
    markup = client.ns.button.build_button_grid(buttons=button_data, row_width=1)
    
    results = [
        InlineQueryResultArticle(
            title="Kirim Permintaan ke Gemini AI",
            description=f"Prompt: {query[:40]}...",
            input_message_content=InputTextMessageContent(placeholder_text),
            thumb_url="https://files.catbox.moe/ozzvtz.jpg",
            reply_markup=markup,
        )
    ]
    try:
        await inline_query.answer(results=results, cache_time=1)
    except QueryIdInvalid:
        pass

@app.on_chosen_inline_result()
async def prefetch_handler(client: Client, chosen_inline_result: ChosenInlineResult):
    asyncio.create_task(
        process_and_cache_gemini(
            user_id=chosen_inline_result.from_user.id,
            query=chosen_inline_result.query
        )
    )

@app.on_callback_query(filters.regex(r"^get_gem:"))
async def answer_from_inline(client: Client, callback_query: CallbackQuery):
    query_id = callback_query.data.split(":", 1)[1]
    user_id = callback_query.from_user.id

    query = db.getVars(user_id, query_id, var_key="TEMP_PROMPTS")
    if not query:
        return await callback_query.answer("Permintaan ini sudah kedaluwarsa atau tidak valid.", show_alert=True)
        
    db.removeVars(user_id, query_id, var_key="TEMP_PROMPTS")
    
    try:
        response_text = db.getVars(user_id, query_id, var_key="CACHED_RESULTS")
        
        if response_text:
            log.info(f"Cache hit untuk user {user_id}, query_id: {query_id}")
            db.removeVars(user_id, query_id, var_key="CACHED_RESULTS")
        else:
            log.warning(f"Cache miss untuk user {user_id}. Memproses secara manual.")
            await callback_query.edit_message_text(f"🤔 **Prompt:**\n`{query}`\n\n⏳ __AI sedang memproses, harap tunggu...__")
            def get_response_sync():
                return chatbot.send_chat_message(message=query, user_id=f"manual_{user_id}", bot_name="GeminiBot")
            response_text = await asyncio.to_thread(get_response_sync)

        final_text = f"🤔 **Prompt:**\n`{query}`\n\n💡 **Jawaban Gemini:**\n{response_text}"
        buttons_data = [
            {"text": "✏️ Ubah & Tanya Lagi", "switch_inline_query_current_chat": query},
            {"text": "💬 Tanya Baru", "switch_inline_query_current_chat": ""}
        ]
        final_markup = client.ns.button.build_button_grid(buttons=buttons_data, row_width=2)
        await callback_query.edit_message_text(final_text, reply_markup=final_markup)

    except Exception as e:
        log.error(f"Error pada callback inline: {e}")
        await callback_query.edit_message_text(
            f"❌ **Terjadi Kesalahan**\n\nMaaf, saya tidak dapat memproses permintaan untuk prompt:\n`{query}`"
        )

if __name__ == "__main__":
    log.print(f"{log.GREEN}Bot Gemini sedang berjalan...")
    app.run()
