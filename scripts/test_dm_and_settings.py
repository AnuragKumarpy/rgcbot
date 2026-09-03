import asyncio
import sys
from telethon import TelegramClient

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
SESSION_PATH = "scripts/user_session"
BOT_USERNAME = "RandomGCCorebot"
GROUP_ID = -1003801913218


async def main():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print(f"🚀 Testing as: {me.first_name} (@{me.username}) [ID: {me.id}]")

    bot = await client.get_entity(BOT_USERNAME)
    group = await client.get_entity(GROUP_ID)

    print("\n--- 1. Testing DM /start with MAU and Inline Buttons ---")
    sent = await client.send_message(bot, "/start")
    await asyncio.sleep(2)
    msgs = await client.get_messages(bot, limit=2)
    start_msg = msgs[0]
    print(f"📥 /start Response:\n{start_msg.text}\n")
    if start_msg.buttons:
        print("🔘 Detected Buttons:")
        for row in start_msg.buttons:
            print([btn.text for btn in row])

    print("\n--- 2. Testing Group /settings with Dual Option Buttons ---")
    g_sent = await client.send_message(group, "/settings")
    await asyncio.sleep(2.5)
    g_msgs = await client.get_messages(group, limit=2)
    g_msg = g_msgs[0]
    print(f"📥 Group /settings Response:\n{g_msg.text}\n")
    if g_msg.buttons:
        print("🔘 Detected Group Buttons:")
        for row in g_msg.buttons:
            print([btn.text for btn in row])

    print("\n--- 3. Testing /adminpanel Command in DM ---")
    ap_sent = await client.send_message(bot, "/adminpanel")
    await asyncio.sleep(2)
    ap_msgs = await client.get_messages(bot, limit=2)
    ap_msg = ap_msgs[0]
    print(f"📥 /adminpanel Response:\n{ap_msg.text}\n")
    if ap_msg.buttons:
        print("🔘 Detected Superadmin Buttons:")
        for row in ap_msg.buttons:
            print([btn.text for btn in row])

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
