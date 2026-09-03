import asyncio
from telethon import TelegramClient

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
SESSION_PATH = "scripts/user_session"
BOT_USERNAME = "RandomGCCorebot"


async def test():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()
    bot = await client.get_entity(BOT_USERNAME)

    print("👉 Sending /adminpanel in DM...")
    sent = await client.send_message(bot, "/adminpanel")
    await asyncio.sleep(2.5)

    msgs = await client.get_messages(bot, limit=4)
    ap_reply = None
    for m in msgs:
        if m.sender_id == bot.id and m.id > sent.id:
            ap_reply = m
            break

    print("📥 /adminpanel Output:\n", ap_reply.text if ap_reply else "No reply")
    if ap_reply and ap_reply.buttons:
        print("🔘 Buttons:", [[b.text for b in row] for row in ap_reply.buttons])

        # Click Broadcast Wizard
        print("\n👉 Clicking '📢 Broadcast Wizard' button...")
        await ap_reply.buttons[0][1].click()
        await asyncio.sleep(2)

        w_msgs = await client.get_messages(bot, limit=2)
        for wm in w_msgs:
            if wm.sender_id == bot.id:
                print("📥 Broadcast Wizard Screen:\n", wm.text)
                break

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test())
