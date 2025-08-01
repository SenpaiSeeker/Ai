clear

echo "=== Konfigurasi Bot Gemini ==="
echo "Harap masukkan detail yang diperlukan di bawah ini."
echo ""

read -p "Masukkan API_ID Anda: " API_ID
read -p "Masukkan API_HASH Anda: " API_HASH
read -p "Masukkan BOT_TOKEN Anda: " BOT_TOKEN
read -p "Masukkan GEMINI_API_KEY Anda: " GEMINI_API_KEY

cat > .env << EOF
# File konfigurasi untuk bot Telegram
# Dihasilkan secara otomatis oleh setup_env.sh

API_ID=${API_ID}
API_HASH="${API_HASH}"
BOT_TOKEN="${BOT_TOKEN}"
GEMINI_API_KEY="${GEMINI_API_KEY}"
EOF

echo ""
echo "✅ File .env berhasil dibuat!"
echo "Sekarang Anda dapat menjalankan bot Anda."
