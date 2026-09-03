import asyncio
import json
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
PHONE = "+919286394869"
SESSION_PATH = "scripts/user_session"


async def main():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"ALREADY_AUTHORIZED:{me.id}:{me.first_name}:{me.username}")
        await client.disconnect()
        return

    sent = await client.send_code_request(PHONE)
    with open("scripts/auth_state.json", "w") as f:
        json.dump({"phone_code_hash": sent.phone_code_hash, "phone": PHONE}, f)

    print(f"CODE_SENT:{sent.phone_code_hash}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
