import asyncio
import json
import sys
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
PHONE = "+919286394869"
SESSION_PATH = "scripts/user_session"
PASSWORD_2FA = "1234"


async def main():
    if len(sys.argv) < 2:
        print("ERROR: Please provide the OTP code. Usage: python complete_login.py <code>")
        return

    code = sys.argv[1].strip()

    with open("scripts/auth_state.json", "r") as f:
        state = json.load(f)

    phone_code_hash = state["phone_code_hash"]

    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()

    try:
        await client.sign_in(phone=PHONE, code=code, phone_code_hash=phone_code_hash)
    except SessionPasswordNeededError:
        print("2FA password required, attempting with provided 2FA password...")
        await client.sign_in(password=PASSWORD_2FA)

    me = await client.get_me()
    print(f"SUCCESS_LOGIN:{me.id}:{me.first_name}:{me.username}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
