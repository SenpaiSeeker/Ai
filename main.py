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

chatbot = app.ns.gemini(api_key=GEMINI_API_KEY)


@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text(
        f"👋 Halo, {message.from_user.first_name}!\n\n"
        "Saya adalah bot AI yang didukung oleh Google Gemini.\n\n"
        f"Gunakan saya secara inline: `@{(await client.get_me()).username} <pertanyaan>`"
    )

@app.on_inline_query()
async def handle_inline_query(client: Client, inline_query: InlineQuery):
    query = inline_query.query.strip()
    if not query:
        return

    placeholder_text = f"🤔 **Prompt:**\n`{query}`\n\n⏳ _AI sedang memproses permintaan Anda..._"
    
    results = [
        InlineQueryResultArticle(
            id=f"gemini_query:{query[:40]}",
            title="Kirim Permintaan ke Gemini AI",
            description=f"Prompt: {query[:50]}...",
            input_message_content=InputTextMessageContent(placeholder_text),
        )
    ]
    try:
        await inline_query.answer(results=results, cache_time=1)
    except QueryIdInvalid:
        pass


@app.on_chosen_inline_result()
async def process_chosen_result(client: Client, chosen_inline_result: ChosenInlineResult):
    query = chosen_inline_result.query.strip()
    inline_message_id = chosen_inline_result.inline_message_id

    if not query or not inline_message_id:
        return

    try:
        inline_user_id = f"chosen_inline_{chosen_inline_result.from_user.id}"
        
        def get_gemini_response():
            return chatbot.send_chat_message(
                message=query, user_id=inline_user_id, bot_name="GeminiBot"
            )
        
        response_text = await asyncio.to_thread(get_gemini_response)

        if inline_user_id in chatbot.chat_history:
            del chatbot.chat_history[inline_user_id]
            
        final_text = f"🤔 **Prompt:**\n`{query}`\n\n💡 **Jawaban Gemini:**\n{response_text}"
        
        edit_query_button = InlineKeyboardButton(
            text="✏️ Ubah & Tanya Lagi", switch_inline_query_current_chat=query
        )
        new_query_button = InlineKeyboardButton(
            text="💬 Tanya Baru", switch_inline_query_current_chat=""
        )
        final_markup = InlineKeyboardMarkup([[edit_query_button, new_query_button]])
        
        await client.edit_inline_text(
            inline_message_id=inline_message_id,
            text=final_text,
            reply_markup=final_markup
        )

    except Exception as e:
        app.ns.log.error(f"Error pada chosen_inline_result: {e}")
        try:
            await client.edit_inline_text(
                inline_message_id=inline_message_id,
                text=f"❌ **Terjadi Kesalahan**\n\nMaaf, saya tidak dapat memproses permintaan untuk prompt:\n`{query}`"
            )
        except Exception as final_error:
            app.ns.log.error(f"Gagal mengedit pesan error inline: {final_error}")


if __name__ == "__main__":
    print("Bot Gemini sedang berjalan...")
    app.run()
