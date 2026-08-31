import asyncio
import os
import random
from telethon import TelegramClient

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
SESSION_PATH = "scripts/user_session"

async def main():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()

    stickers = await client.get_entity("Stickers")
    
    # 1. Reset
    await client.send_message(stickers, "/cancel")
    await asyncio.sleep(1.5)
    
    # 2. Start
    await client.send_message(stickers, "/newemojipack")
    await asyncio.sleep(2)
    
    msgs = await client.get_messages(stickers, limit=2)
    latest = msgs[0]
    print(f"Buttons on @Stickers message: {[[b.text for b in row] for row in latest.buttons] if latest.buttons else 'No buttons'}")
    
    # Click "Animated emoji" button
    if latest.buttons:
        for row in latest.buttons:
            for b in row:
                if "Animated" in b.text:
                    print(f"Clicking button '{b.text}'...")
                    await b.click()
                    break
    
    await asyncio.sleep(2)
    
    # Check reply: Set Title
    msgs = await client.get_messages(stickers, limit=2)
    print(f"Stickers Prompt:\n{msgs[0].text}\n---")
    
    title = "RGCBot Elite Animated"
    await client.send_message(stickers, title)
    await asyncio.sleep(2)
    
    msgs = await client.get_messages(stickers, limit=2)
    print(f"Stickers Prompt:\n{msgs[0].text}\n---")
    
    # Upload 6 emojis
    files = [
        ("emojis_to_upload/NewsEmoji_2.tgs", "⚡️"),
        ("emojis_to_upload/NewsEmoji_0.tgs", "👀"),
        ("emojis_to_upload/Topics_1.tgs", "💡"),
        ("emojis_to_upload/Topics_4.tgs", "🔝"),
        ("emojis_to_upload/marketment_0.tgs", "💎"),
        ("emojis_to_upload/marketment_2.tgs", "🧠"),
    ]
    
    for path, alt in files:
        if os.path.exists(path):
            print(f"Uploading {path}...")
            await client.send_file(stickers, path, force_document=True)
            await asyncio.sleep(2.5)
            await client.send_message(stickers, alt)
            await asyncio.sleep(2)

    # Publish
    print("Publishing...")
    await client.send_message(stickers, "/publish")
    await asyncio.sleep(2)
    
    # Skip icon
    await client.send_message(stickers, "/skip")
    await asyncio.sleep(2)
    
    # Short name
    short_name = f"rgcbot_elite_{random.randint(100, 999)}"
    await client.send_message(stickers, short_name)
    await asyncio.sleep(3)
    
    final_msgs = await client.get_messages(stickers, limit=3)
    for m in final_msgs:
        print(f"Final Message:\n{m.text}\n---")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
