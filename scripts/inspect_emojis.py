import asyncio
from telethon import TelegramClient
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetShortName

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
SESSION_PATH = "scripts/user_session"

EMOJI_PACKS = ["NewsEmoji", "Topics", "marketment"]


async def inspect_packs():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()

    print("==================================================")
    print("🔍 Fetching Custom Emoji IDs from Packs...")
    print("==================================================")

    extracted_emojis = {}

    for pack_name in EMOJI_PACKS:
        try:
            res = await client(
                GetStickerSetRequest(
                    stickerset=InputStickerSetShortName(short_name=pack_name), hash=0
                )
            )
            print(f"\n📦 Pack: {res.set.title} (@{pack_name}) - Total Emojis: {len(res.documents)}")
            extracted_emojis[pack_name] = []
            for doc in res.documents[:10]:  # inspect first 10
                # find alt text attribute if present
                alt = "✨"
                for attr in doc.attributes:
                    if hasattr(attr, "alt") and attr.alt:
                        alt = attr.alt
                print(f"  • ID: {doc.id} | Alt: {alt} | Mime: {doc.mime_type}")
                extracted_emojis[pack_name].append({"id": doc.id, "alt": alt})
        except Exception as e:
            print(f"❌ Error fetching pack {pack_name}: {e}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(inspect_packs())
