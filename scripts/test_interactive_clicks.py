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

    # 1. Send /start in DM
    sent = await client.send_message(bot, "/start")
    await asyncio.sleep(3)
    msgs = await client.get_messages(bot, limit=5)
    start_reply = None
    for m in msgs:
        if m.sender_id == bot.id and m.id > sent.id:
            start_reply = m
            break

    print("==================================================")
    print("📥 DM /start Reply Text:\n", start_reply.text if start_reply else "No reply")
    if start_reply and start_reply.buttons:
        print("🔘 Buttons:", [[b.text for b in row] for row in start_reply.buttons])

        # 2. Click "👑 Super Admin Control Panel" Button
        print("\n👉 Clicking '👑 Super Admin Control Panel' inline button...")
        for row in start_reply.buttons:
            for b in row:
                if "Super Admin" in b.text:
                    await b.click()
                    break

        await asyncio.sleep(3)
        updated_msgs = await client.get_messages(bot, limit=3)
        for m in updated_msgs:
            if m.sender_id == bot.id:
                print("📥 Screen after clicking Super Admin button:\n", m.text)
                if m.buttons:
                    print("🔘 Admin Panel Buttons:", [[b.text for b in row] for row in m.buttons])
                break

        # 3. Click "⚙️ Group Settings" Button
        print("\n👉 Clicking '⚙️ Group Settings' button...")
        # send /settings in DM
        s_sent = await client.send_message(bot, "/settings")
        await asyncio.sleep(3)
        s_msgs = await client.get_messages(bot, limit=5)
        for m in s_msgs:
            if m.sender_id == bot.id and m.id > s_sent.id:
                print("📥 Screen after sending /settings in DM:\n", m.text)
                if m.buttons:
                    print("🔘 Managed Group Buttons:", [[b.text for b in row] for row in m.buttons])
                    # Click first group button
                    print(f"👉 Clicking group button '{m.buttons[0][0].text}'...")
                    await m.buttons[0][0].click()
                    await asyncio.sleep(3)
                    g_cfg_msgs = await client.get_messages(bot, limit=3)
                    for gm in g_cfg_msgs:
                        if gm.sender_id == bot.id:
                            print("📥 Remote Group Settings Dashboard opened in DM:\n", gm.text)
                            if gm.buttons:
                                print(
                                    "🔘 Remote Group Control Buttons:",
                                    [[b.text for b in row] for row in gm.buttons],
                                )
                            break
                break

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test())
