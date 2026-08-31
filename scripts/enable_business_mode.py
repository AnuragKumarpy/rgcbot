import asyncio
from telethon import TelegramClient

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
SESSION_PATH = "scripts/user_session"
BOT_USERNAME = "@RandomGCCorebot"

async def enable_business():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()

    botfather = await client.get_entity("BotFather")
    print(f"Connected to @BotFather (ID: {botfather.id})")

    # 1. Send /cancel
    await client.send_message(botfather, "/cancel")
    await asyncio.sleep(1.5)

    # 2. Send /mybots
    await client.send_message(botfather, "/mybots")
    await asyncio.sleep(2)

    msgs = await client.get_messages(botfather, limit=2)
    latest = msgs[0]
    print(f"BotFather Menu:\n{latest.text}\nButtons: {[[b.text for b in row] for row in latest.buttons] if latest.buttons else 'None'}")

    # Click @RandomGCCorebot button
    if latest.buttons:
        for row in latest.buttons:
            for b in row:
                if "RandomGCCorebot" in b.text or "RandomGC" in b.text or "8678007987" in b.text:
                    print(f"Clicking bot button '{b.text}'...")
                    await b.click()
                    break

    await asyncio.sleep(2)
    msgs = await client.get_messages(botfather, limit=2)
    latest = msgs[0]
    print(f"\nBot Selected Menu:\n{latest.text}\nButtons: {[[b.text for b in row] for row in latest.buttons] if latest.buttons else 'None'}")

    # Click "Bot Settings"
    if latest.buttons:
        for row in latest.buttons:
            for b in row:
                if "Bot Settings" in b.text:
                    print(f"Clicking '{b.text}'...")
                    await b.click()
                    break

    await asyncio.sleep(2)
    msgs = await client.get_messages(botfather, limit=2)
    latest = msgs[0]
    print(f"\nBot Settings Menu:\n{latest.text}\nButtons: {[[b.text for b in row] for row in latest.buttons] if latest.buttons else 'None'}")

    # Check for "Business Mode" or "Telegram Business" button
    if latest.buttons:
        for row in latest.buttons:
            for b in row:
                if "Business" in b.text:
                    print(f"Clicking '{b.text}'...")
                    await b.click()
                    await asyncio.sleep(2)
                    b_msgs = await client.get_messages(botfather, limit=2)
                    b_latest = b_msgs[0]
                    print(f"\nBusiness Menu:\n{b_latest.text}\nButtons: {[[b.text for b in row] for row in b_latest.buttons] if b_latest.buttons else 'None'}")
                    if b_latest.buttons:
                        for brow in b_latest.buttons:
                            for bb in brow:
                                if "Turn on" in bb.text or "Enable" in bb.text or "Yes" in bb.text:
                                    print(f"Clicking '{bb.text}'...")
                                    await bb.click()
                                    await asyncio.sleep(2)
                    break

    final_msgs = await client.get_messages(botfather, limit=2)
    print(f"\nFinal BotFather Message:\n{final_msgs[0].text}\n---")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(enable_business())
