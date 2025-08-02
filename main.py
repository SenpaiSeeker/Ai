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

log = app.ns.log()
log.fmt = "{asctime} {levelname} {message}"


@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text(
        f"👋 Halo, {message.from_user.first_name}!\n\n"
        "Saya adalah bot AI yang didukung oleh Google Gemini.\n\n"
        f"Gunakan saya melalui mode inline (`@{(await client.get_me()).username} [pertanyaan]`) untuk memulai. "
        "Setiap permintaan yang Anda proses akan disimpan ke dalam riwayat percakapan Anda."
    )


@app.on_message(filters.command("clear") & filters.private)
async def clear_command(client: Client, message: Message):
    user_id = message.from_user.id
    db.removeVars(user_id, "GEMINI_HISTORY")
    if user_id in chatbot.chat_history:
        del chatbot.chat_history[user_id]
    await message.reply_text("✅ Riwayat percakapan Anda telah berhasil dihapus.")


@app.on_inline_query()
async def handle_inline_query(client: Client, inline_query: InlineQuery):
    query = inline_query.query.strip()
    if not query:
        return

    query_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, query).hex)
    db.setVars(inline_query.from_user.id, query_id, query, var_key="TEMP_PROMPTS")

    callback_data = f"get_gem:{query_id}"
    
    placeholder_text = f"🤔 **Prompt:**\n`{query}`\n\n__Klik tombol di bawah untuk memproses...__"
    
    button_data = [
        {
            "text": "⏳ Proses Permintaan AI",
            "callback_data": callback_data,
        }
    ]
    
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


@app.on_callback_query(filters.regex(r"^get_gem:"))
async def answer_from_inline(client: Client, callback_query: CallbackQuery):
    query_id = callback_query.data.split(":", 1)[1]
    user_id = callback_query.from_user.id

    query = db.getVars(user_id, query_id, var_key="TEMP_PROMPTS")

    if not query:
        await callback_query.answer("Permintaan ini sudah kedaluwarsa atau tidak valid.", show_alert=True)
        try:
            await callback_query.edit_message_text("❌ Permintaan ini sudah tidak valid lagi.")
        except Exception:
            pass
        return
    
    db.removeVars(user_id, query_id, var_key="TEMP_PROMPTS")

    try:
        await callback_query.edit_message_text(f"🤔 **Prompt:**\n`{query}`\n\n⏳ __AI sedang memproses, harap tunggu...__")
    except Exception as e:
        log.warning(f"Gagal edit pesan awal callback: {e}")

    try:
        history = db.getVars(user_id, "GEMINI_HISTORY") or []
        chatbot.chat_history[user_id] = history

        def get_response_with_history():
            return chatbot.send_chat_message(
                message=query, user_id=user_id, bot_name="GeminiBot"
            )
        response_text = await asyncio.to_thread(get_response_with_history)

        updated_history = chatbot.chat_history.get(user_id, [])
        db.setVars(user_id, "GEMINI_HISTORY", updated_history)

        final_text = f"🤔 **Prompt:**\n`{query}`\n\n💡 **Jawaban Gemini:**\n{response_text}"
        
        buttons_data = [
            {
                "text": "✏️ Ubah & Tanya Lagi",
                "switch_inline_query_current_chat": query
            },
            {
                "text": "💬 Tanya Baru",
                "switch_inline_query_current_chat": ""
            }
        ]

        final_markup = client.ns.button.build_button_grid(
            buttons=buttons_data, 
            row_width=2
        )
        
        await callback_query.edit_message_text(final_text, reply_markup=final_markup)

    except Exception as e:
        log.error(f"Error pada callback inline: {e}")
        await callback_query.edit_message_text(
            f"❌ **Terjadi Kesalahan**\n\nMaaf, saya tidak dapat memproses permintaan untuk prompt:\n`{query}`"
        )


if __name__ == "__main__":
    log.info("Bot Gemini sedang berjalan...")
    app.run()
