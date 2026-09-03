import asyncio
import sys
from telethon import TelegramClient

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
SESSION_PATH = "scripts/user_session"
BOT_USERNAME = "RandomGCCorebot"
TARGET_CHAT_ID = -1003801913218  # "Random GC"


async def test_bot():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print(f"==================================================")
    print(f"🚀 Logged in as: {me.first_name} (@{me.username}) [ID: {me.id}]")
    print(f"==================================================")

    bot_entity = await client.get_entity(BOT_USERNAME)
    print(f"🤖 Connected to Bot: @{BOT_USERNAME} (ID: {bot_entity.id})")

    # 1. Test Supergroup Commands in "Random GC"
    try:
        group_entity = await client.get_entity(TARGET_CHAT_ID)
        print(f"\n==================================================")
        print(f"🛡️ Testing Group Commands in: {group_entity.title} [{TARGET_CHAT_ID}]")
        print(f"==================================================")

        group_cmds = [
            "/settings",
            "/zombies",
            "/blocklist",
            "/welcome",
            "/rules",
            "/slots",
            "/roulette",
            "/topkarma",
            "/panic",
            "/panic off",
        ]

        for g_cmd in group_cmds:
            print(f"\n👉 [Group] Sending: {g_cmd}")
            sent = await client.send_message(group_entity, g_cmd)
            await asyncio.sleep(3)

            # Fetch latest 3 messages in group
            g_msgs = await client.get_messages(group_entity, limit=3)
            for m in g_msgs:
                if m.sender_id == bot_entity.id:
                    print(f"📥 Bot Reply to [{g_cmd}]:\n{m.text}\n---")
                    break

    except Exception as e:
        print(f"Error testing in group {TARGET_CHAT_ID}: {e}")

    # 2. Check Log Channel for Audit Delivery
    try:
        log_channel = await client.get_entity(-1004381062510)
        print(f"\n==================================================")
        print(f"📡 Verifying Audit Channel: {log_channel.title} [{log_channel.id}]")
        print(f"==================================================")
        logs = await client.get_messages(log_channel, limit=8)
        for l in logs:
            print(f"📝 Audit Record [{l.date}]:\n{l.text}\n---")
    except Exception as e:
        print(f"Could not inspect log channel: {e}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_bot())
