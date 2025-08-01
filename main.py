import os
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
    InlineKeyboardMarkup,
    InlineKeyboardButton,
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

db = app.ns.db(
    storage_type="local",
    file_name="gemini_chat_history",
    keys_encrypt="kunci_rahasia_untuk_db_chat",
)

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
        history = db.getVars(user_id, "GEMINI_HISTORY") or []
        chatbot.chat_history[user_id] = history
        def get_gemini_response():
            return chatbot.send_chat_message(
                message=user_input, user_id=user_id, bot_name="GeminiBot"
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

    callback_data = f"get_gem:{query[:50]}"
    
    placeholder_text = f"🤔 **Prompt:**\n`{query}`\n\n_Klik tombol di bawah untuk memproses..._"
    
    results = [
        InlineQueryResultArticle(
            title="Kirim Permintaan ke Gemini AI",
            description=f"Prompt: {query[:40]}...",
            input_message_content=InputTextMessageContent(placeholder_text),
            thumb_url="https://i.imgur.com/nwJdA52.png",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="⏳ Proses Permintaan AI",
                            callback_data=callback_data,
                        )
                    ]
                ]
            ),
        )
    ]
    try:
        await inline_query.answer(results=results, cache_time=1)
    except QueryIdInvalid:
        pass


@app.on_callback_query(filters.regex(r"^get_gem:"))
async def answer_from_inline(client: Client, callback_query: CallbackQuery):
    query = callback_query.data.split(":", 1)[1]

    try:
        await callback_query.edit_message_text(f"🤔 **Prompt:**\n`{query}`\n\n⏳ _AI sedang memproses, harap tunggu..._")
    except Exception as e:
        app.ns.log.warning(f"Gagal edit pesan awal callback: {e}")


    try:
        inline_user_id = f"inline_callback_{callback_query.from_user.id}"
        def get_inline_response():
            return chatbot.send_chat_message(
                message=query, user_id=inline_user_id, bot_name="GeminiBot"
            )
        response_text = await asyncio.to_thread(get_inline_response)
            
        final_text = f"🤔 **Prompt:**\n`{query}`\n\n💡 **Jawaban Gemini:**\n{response_text}"
        
        edit_query_button = InlineKeyboardButton(
            text="✏️ Ubah & Tanya Lagi", switch_inline_query_current_chat=query
        )
        new_query_button = InlineKeyboardButton(
            text="💬 Tanya Baru", switch_inline_query_current_chat=""
        )
        final_markup = InlineKeyboardMarkup([[edit_query_button, new_query_button]])
        
        await callback_query.edit_message_text(final_text, reply_markup=final_markup)

    except Exception as e:
        app.ns.log.error(f"Error pada callback inline: {e}")
        await callback_query.edit_message_text(
            f"❌ **Terjadi Kesalahan**\n\nMaaf, saya tidak dapat memproses permintaan untuk prompt:\n`{query}`"
        )


if __name__ == "__main__":
    print("Bot Gemini sedang berjalan...")
    app.run()
