import os
import asyncio
from dotenv import load_dotenv

# Impor dari Telethon
from telethon import TelegramClient, events, Button

import nsdev

load_dotenv()

# Konfigurasi tetap sama
API_ID = int(os.getenv("API_ID")) # Telethon butuh integer
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inisialisasi Klien Telethon
# 'gemini_bot.session' akan dibuat untuk menyimpan sesi
app = TelegramClient("gemini_bot", API_ID, API_HASH)

# Inisialisasi norsodikin (tidak terintegrasi otomatis, kita panggil manual)
chatbot = nsdev.ChatbotGemini(api_key=GEMINI_API_KEY)
log = nsdev.LoggerHandler()
button_builder = nsdev.Button() # Kita tidak bisa pakai client.ns, jadi panggil langsung


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

    # Builder adalah cara mudah Telethon untuk membuat hasil inline
    builder = event.builder

    # Ini adalah hasil placeholder yang langsung dikirim
    placeholder = builder.article(
        title='⏳ Memproses...',
        description='AI sedang berpikir, harap tunggu sebentar.',
        text='Sedang menunggu jawaban dari AI...'
    )

    try:
        # Kirim placeholder SEGERA
        await event.answer([placeholder])
    except Exception:
        # Jika pengguna mengetik terlalu cepat, abaikan saja
        return

    # SEKARANG, proses permintaan AI di background.
    # Tidak perlu asyncio.create_task(), Telethon menangani ini dengan baik.
    try:
        def get_response_sync():
            return chatbot.send_chat_message(
                message=query,
                user_id=f"inline_{event.sender_id}",
                bot_name="GeminiBot"
            )
        response_text = await asyncio.to_thread(get_response_sync)
        
        final_text = f"🤔 **Prompt:**\n`{query}`\n\n💡 **Jawaban Gemini:**\n{response_text}"

        # Membuat tombol dengan sintaks Telethon
        final_buttons = [
            [
                Button.switch_inline("✏️ Ubah & Tanya Lagi", query, current_chat=True),
                Button.switch_inline("💬 Tanya Baru", "", current_chat=True)
            ]
        ]
        
        # Buat hasil final
        final_article = builder.article(
            title="Jawaban dari Gemini AI",
            description=response_text.replace("\n", " ")[:60],
            text=final_text,
            link_preview=False, # Supaya tidak ada preview link
            buttons=final_buttons,
            thumb=builder.photo(file="https://files.catbox.moe/ozzvtz.jpg")
        )

        # KIRIM JAWABAN FINAL UNTUK MENGGANTIKAN PLACEHOLDER
        # Telethon akan secara otomatis memperbarui hasil di menu pengguna.
        await event.answer([final_article])

    except Exception as e:
        log.error(f"Error pada inline query handler: {e}")
        # Jika terjadi error, kita juga bisa memperbarui hasilnya
        error_article = builder.article(
            title="❌ Terjadi Kesalahan",
            description="Tidak dapat memproses permintaan Anda.",
            text=f"❌ Gagal memproses prompt: `{query}`"
        )
        try:
            await event.answer([error_article])
        except Exception:
            pass # Abaikan jika query sudah tidak valid


async def main():
    """Fungsi utama untuk menjalankan bot."""
    await app.start(bot_token=BOT_TOKEN)
    log.print(f"{log.GREEN}Bot Gemini (Telethon) sedang berjalan...")
    await app.run_until_disconnected()


if __name__ == '__main__':
    asyncio.run(main())
