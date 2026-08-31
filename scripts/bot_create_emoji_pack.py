import asyncio
import os
from aiogram import Bot
from aiogram.types import FSInputFile, InputSticker
from telethon import TelegramClient
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetShortName

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
USER_ID = 8713594643
API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
SESSION_PATH = "scripts/user_session"

SOURCE_PACKS = ["NewsEmoji", "Topics", "marketment"]

async def main():
    # 1. Download animated emojis using Telethon
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()
    
    os.makedirs("emojis_bot_pack", exist_ok=True)
    emoji_items = []
    
    for pack in SOURCE_PACKS:
        try:
            res = await client(GetStickerSetRequest(stickerset=InputStickerSetShortName(short_name=pack), hash=0))
            for i, doc in enumerate(res.documents[:6]):
                alt = "⚡️"
                for a in doc.attributes:
                    if hasattr(a, 'alt') and a.alt:
                        alt = a.alt
                filename = f"emojis_bot_pack/{pack}_{i}.tgs"
                if not os.path.exists(filename):
                    await client.download_media(doc, file=filename)
                emoji_items.append((filename, alt))
                print(f"Prepared {filename} ({alt})")
        except Exception as e:
            print(f"Error downloading from {pack}: {e}")
            
    await client.disconnect()

    # 2. Create Custom Emoji Set using Bot API
    bot = Bot(token=BOT_TOKEN)
    bot_info = await bot.get_me()
    print(f"\nBot: @{bot_info.username} (ID: {bot_info.id})")
    
    import random
    set_name = f"rgc_elite_{random.randint(10, 99)}_by_{bot_info.username}"
    title = "RGCBot Elite Custom Emojis"
    
    input_stickers = []
    for filepath, alt in emoji_items[:12]:
        input_stickers.append(
            InputSticker(
                sticker=FSInputFile(filepath),
                format="animated",
                emoji_list=[alt],
            )
        )
        
    print(f"Creating custom emoji set '{set_name}' with {len(input_stickers)} emojis...")
    try:
        res = await bot.create_new_sticker_set(
            user_id=USER_ID,
            name=set_name,
            title=title,
            stickers=input_stickers,
            sticker_type="custom_emoji",
        )
        print(f"Pack creation success: {res}")
    except Exception as e:
        print(f"Error creating sticker set: {e}")
        
    # Retrieve the sticker set to get exact custom emoji document IDs
    try:
        created_set = await bot.get_sticker_set(name=set_name)
        print(f"\nCreated Set: {created_set.title} ({created_set.name})")
        print(f"Total Custom Emojis: {len(created_set.stickers)}")
        for s in created_set.stickers:
            print(f"Emoji: {s.emoji} | Custom Emoji ID: {s.custom_emoji_id}")
    except Exception as e:
        print(f"Error fetching created set: {e}")

    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
