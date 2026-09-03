import asyncio
from telethon import TelegramClient

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
SESSION_PATH = "scripts/user_session"


async def toggle_secretary():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()

    botfather = await client.get_entity("BotFather")

    msgs = await client.get_messages(botfather, limit=2)
    latest = msgs[0]
    print(
        f"Current Menu:\n{latest.text}\nButtons: {[[b.text for b in row] for row in latest.buttons] if latest.buttons else 'None'}"
    )

    # Click "Secretary Mode"
    if latest.buttons:
        for row in latest.buttons:
            for b in row:
                if "Secretary" in b.text or "Business" in b.text:
                    print(f"Clicking '{b.text}'...")
                    await b.click()
                    break

    await asyncio.sleep(2)
    msgs = await client.get_messages(botfather, limit=2)
    latest = msgs[0]
    print(
        f"\nSecretary Mode Menu:\n{latest.text}\nButtons: {[[b.text for b in row] for row in latest.buttons] if latest.buttons else 'None'}"
    )

    # Click "Turn on" or "Enable"
    if latest.buttons:
        for row in latest.buttons:
            for b in row:
                if "Turn on" in b.text or "Enable" in b.text:
                    print(f"Clicking '{b.text}'...")
                    await b.click()
                    break

    await asyncio.sleep(2)
    final_msgs = await client.get_messages(botfather, limit=2)
    print(f"\nFinal Result:\n{final_msgs[0].text}\n---")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(toggle_secretary())
