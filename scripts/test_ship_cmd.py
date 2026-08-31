import asyncio
from telethon import TelegramClient

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
SESSION_PATH = "scripts/user_session"
BOT_USERNAME = "RandomGCCorebot"
GROUP_ID = -1003801913218

async def test():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()
    bot = await client.get_entity(BOT_USERNAME)
    group = await client.get_entity(GROUP_ID)

    print("👉 Sending /ship in Random GC...")
    sent = await client.send_message(group, "/ship@RandomGCCorebot")
    await asyncio.sleep(3)
    
    msgs = await client.get_messages(group, limit=4)
    ship_msg = None
    for m in msgs:
        if m.sender_id == bot.id and m.id > sent.id:
            ship_msg = m
            break

    print("📥 /ship Response:\n", ship_msg.text if ship_msg else "No reply")
    if ship_msg and ship_msg.buttons:
        print("🔘 Detected Buttons:", [[b.text for b in row] for row in ship_msg.buttons])
        
        # Test clicking Re-roll button
        print("\n👉 Clicking '🔄 Roll New Ship' button...")
        await ship_msg.buttons[0][0].click()
        await asyncio.sleep(2)
        updated = await client.get_messages(group, ids=ship_msg.id)
        print("📥 Updated /ship Screen after re-roll:\n", updated.text)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test())
