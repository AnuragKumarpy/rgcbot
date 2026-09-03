import asyncio
from aiogram import Bot
from src.config.settings import settings

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TEST_USER_ID = 8713594643


async def main():
    bot = Bot(token=BOT_TOKEN)

    # Testing Custom Emojis from NewsEmoji, Topics, marketment
    text = (
        "<b>💎 PREMIUM CUSTOM EMOJI TEST</b>\n\n"
        '• News Emoji: <tg-emoji emoji-id="5456140674028019486">⚡️</tg-emoji> <tg-emoji emoji-id="5210956306952758910">👀</tg-emoji> <tg-emoji emoji-id="5440660757194744323">‼️</tg-emoji>\n'
        '• Topics Pack: <tg-emoji emoji-id="5434144690511290129">📰</tg-emoji> <tg-emoji emoji-id="5312536423851630001">💡</tg-emoji> <tg-emoji emoji-id="5418085807791545980">🔝</tg-emoji>\n'
        '• Marketment Pack: <tg-emoji emoji-id="5800688138833629633">💎</tg-emoji> <tg-emoji emoji-id="5801027411185242471">🧠</tg-emoji> <tg-emoji emoji-id="5800781378278658230">🔒</tg-emoji>\n\n'
        "<i>Testing custom emoji rendering across all 3 requested packs!</i>"
    )

    try:
        sent = await bot.send_message(chat_id=TEST_USER_ID, text=text, parse_mode="HTML")
        print(f"✅ Success! Sent custom emoji message (ID: {sent.message_id})")
    except Exception as e:
        print(f"❌ Failed to send custom emoji: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
