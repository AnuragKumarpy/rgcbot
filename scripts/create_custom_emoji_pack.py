import asyncio
import os
from telethon import TelegramClient
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetShortName

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
SESSION_PATH = "scripts/user_session"

SOURCE_PACKS = ["NewsEmoji", "Topics", "marketment"]

async def create_pack():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()

    stickers_bot = await client.get_entity("Stickers")
    print(f"Connected to @Stickers bot (ID: {stickers_bot.id})")

    # 1. Download best emojis from source packs
    os.makedirs("emojis_to_upload", exist_ok=True)
    emoji_files = []
    
    for pack in SOURCE_PACKS:
        try:
            res = await client(GetStickerSetRequest(stickerset=InputStickerSetShortName(short_name=pack), hash=0))
            for i, doc in enumerate(res.documents[:5]):
                alt = "✨"
                for a in doc.attributes:
                    if hasattr(a, 'alt') and a.alt:
                        alt = a.alt
                filename = f"emojis_to_upload/{pack}_{i}.tgs"
                await client.download_media(doc, file=filename)
                emoji_files.append((filename, alt))
                print(f"Downloaded {filename} ({alt})")
        except Exception as e:
            print(f"Error downloading from {pack}: {e}")

    print(f"\n📦 Prepared {len(emoji_files)} animated custom emojis for creation.")

    # 2. Interact with @Stickers
    print("\n--- Sending /cancel to @Stickers ---")
    await client.send_message(stickers_bot, "/cancel")
    await asyncio.sleep(1.5)

    print("--- Sending /newemojipack to @Stickers ---")
    await client.send_message(stickers_bot, "/newemojipack")
    await asyncio.sleep(2)

    msgs = await client.get_messages(stickers_bot, limit=2)
    print(f"Stickers Reply: {msgs[0].text}")

    # Choose Animated emoji pack
    await client.send_message(stickers_bot, "Animated")
    await asyncio.sleep(2)
    msgs = await client.get_messages(stickers_bot, limit=2)
    print(f"Stickers Reply: {msgs[0].text}")

    # Choose Title
    pack_title = "RGCBot Elite Animated"
    await client.send_message(stickers_bot, pack_title)
    await asyncio.sleep(2)
    msgs = await client.get_messages(stickers_bot, limit=2)
    print(f"Stickers Reply: {msgs[0].text}")

    # Upload first 10 emojis
    for filepath, alt in emoji_files[:10]:
        print(f"Uploading {filepath} with alt {alt}...")
        await client.send_file(stickers_bot, filepath, force_document=True)
        await asyncio.sleep(2.5)
        await client.send_message(stickers_bot, alt)
        await asyncio.sleep(2)

    # Publish pack
    print("--- Publishing Pack ---")
    await client.send_message(stickers_bot, "/publish")
    await asyncio.sleep(2)

    # Set icon skip
    await client.send_message(stickers_bot, "/skip")
    await asyncio.sleep(2)

    # Set short name
    import random
    short_name = f"rgcbot_elite_{random.randint(100, 999)}"
    await client.send_message(stickers_bot, short_name)
    await asyncio.sleep(3)

    final_msgs = await client.get_messages(stickers_bot, limit=3)
    for m in final_msgs:
        print(f"Final Reply from @Stickers:\n{m.text}\n---")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(create_pack())
