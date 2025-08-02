import os
import asyncio
from dotenv import load_dotenv

from telethon import TelegramClient, events, Button

import nsdev

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

app = TelegramClient("gemini_bot", API_ID, API_HASH)

chatbot = nsdev.ChatbotGemini(api_key=GEMINI_API_KEY)
log = nsdev.LoggerHandler()


@app.on(events.NewMessage(pattern='/start', func=lambda e: e.is_private))
async def start_handler(event):
    me = await app.get_me()
    await event.respond(
        f"👋 Halo, {event.sender.first_name}!\n\n"
        "Saya adalah bot AI Gemini yang bekerja via inline.\n\n"
        f"Ketik `@{me.username} [pertanyaan]` di chat manapun untuk mendapatkan jawaban langsung."
    )


@app.on(events.InlineQuery)
async def inline_query_handler(event):
    query = event.text.strip()
    if not query:
        return

    builder = event.builder

    placeholder = builder.article(
        title='⏳ Memproses...',
        description='AI sedang berpikir, harap tunggu sebentar.',
        text='Sedang menunggu jawaban dari AI...'
    )

    try:
        await event.answer([placeholder])
    except Exception:
        return

    try:
        def get_response_sync():
            return chatbot.send_chat_message(
                message=query,
                user_id=f"inline_{event.sender_id}",
                bot_name="GeminiBot"
            )
        response_text = await asyncio.to_thread(get_response_sync)
        
        final_text = f"🤔 **Prompt:**\n`{query}`\n\n💡 **Jawaban Gemini:**\n{response_text}"

        final_buttons = [
            [
                Button.switch_inline("✏️ Ubah & Tanya Lagi", query, same_peer=True),
                Button.switch_inline("💬 Tanya Baru", "", same_peer=True)
            ]
        ]
        
        final_article = builder.article(
            title="Jawaban dari Gemini AI",
            description=response_text.replace("\n", " ")[:60],
            text=final_text,
            link_preview=False,
            buttons=final_buttons,
            thumb=builder.photo(file="https://files.catbox.moe/ozzvtz.jpg")
        )

        await event.answer([final_article])

    except Exception as e:
        log.error(f"Error pada inline query handler: {e}")
        error_article = builder.article(
            title="❌ Terjadi Kesalahan",
            description="Tidak dapat memproses permintaan Anda.",
            text=f"❌ Gagal memproses prompt: `{query}`"
        )
        try:
            await event.answer([error_article])
        except Exception:
            pass


async def main():
    await app.start(bot_token=BOT_TOKEN)
    log.print(f"{log.GREEN}Bot Gemini (Telethon) sedang berjalan...")
    await app.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())
