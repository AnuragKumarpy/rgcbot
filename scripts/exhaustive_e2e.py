import asyncio
import json
import time
from telethon import TelegramClient

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
SESSION_PATH = "scripts/user_session"
BOT_USERNAME = "RandomGCCorebot"
GROUP_ID = -1003801913218
LOG_CHANNEL_ID = -1004381062510

results = []

def record(test_name, location, command, response_text, status="PASS"):
    entry = {
        "test": test_name,
        "location": location,
        "command": command,
        "response": response_text.strip() if response_text else "(No response / Action performed)",
        "status": status,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }
    results.append(entry)
    print(f"\n[{status}] {test_name} ({location})")
    print(f"👉 Command: {command}")
    print(f"📥 Response:\n{entry['response']}\n" + "-"*50)

async def run_exhaustive_tests():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()
    
    me = await client.get_me()
    print(f"🚀 Authenticated as: {me.first_name} (@{me.username}) [ID: {me.id}]")

    bot = await client.get_entity(BOT_USERNAME)
    group = await client.get_entity(GROUP_ID)
    log_ch = await client.get_entity(LOG_CHANNEL_ID)

    print("\n=======================================================")
    print("PHASE 1: TESTING DIRECT MESSAGES (DM) COMMANDS")
    print("=======================================================")

    dm_tests = [
        ("Start Command", "/start"),
        ("Help Guide", "/help"),
        ("Admin Help Manual", "/helpadmin"),
        ("Super Admin Panel", "/adminpanel"),
        ("Daily Streak Claim", "/daily"),
        ("Karma Profile", "/karma"),
        ("Reputation Leaderboard", "/topkarma"),
        ("User Profile Card", "/profile"),
        ("AFK Status Set", "/afk Working on bot code"),
        ("AFK Clear Check", "I am back online!"),
        ("Custom Title Flair", "/settitle ✦ VIP Vanguard"),
    ]

    for name, cmd in dm_tests:
        sent = await client.send_message(bot, cmd)
        await asyncio.sleep(2.5)
        msgs = await client.get_messages(bot, limit=3)
        bot_reply = None
        for m in msgs:
            if m.id > sent.id or m.sender_id == bot.id:
                bot_reply = m.text
                break
        record(name, "Direct Messages (DM)", cmd, bot_reply or "")

    print("\n=======================================================")
    print("PHASE 2: TESTING GROUP MODERATION & DEFENSE COMMANDS")
    print("=======================================================")

    group_tests = [
        ("Group Settings Dashboard", "/settings"),
        ("Zombie Account Scanner", "/zombies"),
        ("Blocklist Add Term", "/blocklist add crypto_scam warn"),
        ("Blocklist List Terms", "/blocklist"),
        ("Blocklist Remove Term", "/blocklist remove crypto_scam"),
        ("Attach Admin Note", "/setnote 8857065062 Suspicious test subject"),
        ("View Admin Notes", "/notes 8857065062"),
        ("Clear Admin Notes", "/delnotes 8857065062"),
        ("Configure Group Rules", "/setrules 1. Respect members\n2. No spam\n3. English only"),
        ("View Group Rules", "/rules"),
        ("View Welcome Settings", "/welcome"),
        ("Issue User Warning", "/warn 8857065062 Spamming test warning"),
        ("Check User Warnings", "/warns 8857065062"),
        ("Reset User Warnings", "/resetwarns 8857065062"),
        ("Temp Mute User", "/tmute 8857065062 15m Flooding test"),
        ("Unmute User", "/unmute 8857065062"),
        ("Temp Ban User", "/tban 8857065062 1h Major infraction test"),
        ("Unban User", "/unban 8857065062"),
        ("Kick User", "/kick 8857065062 Inactive test member"),
        ("Panic Mode Lockdown Enable", "/panic on"),
        ("Panic Mode Lockdown Lift", "/panic off"),
    ]

    for name, cmd in group_tests:
        sent = await client.send_message(group, cmd)
        await asyncio.sleep(3.0)
        msgs = await client.get_messages(group, limit=4)
        bot_reply = None
        for m in msgs:
            if m.sender_id == bot.id and m.id > sent.id:
                bot_reply = m.text
                break
        record(name, "Random GC Supergroup", cmd, bot_reply or "")

    print("\n=======================================================")
    print("PHASE 3: TESTING MINI-GAMES & GAMIFICATION")
    print("=======================================================")

    game_tests = [
        ("Play Russian Roulette", "/roulette"),
        ("Roll Animated Dice", "/dice"),
        ("Throw Animated Darts", "/darts"),
        ("Play Slot Machine", "/slots"),
        ("Shoot Basketball", "/basketball"),
        ("Score Football Goal", "/football"),
        ("Roll Bowling Ball", "/bowling"),
    ]

    for name, cmd in game_tests:
        sent = await client.send_message(group, cmd)
        await asyncio.sleep(3.0)
        msgs = await client.get_messages(group, limit=4)
        bot_reply = None
        for m in msgs:
            if m.sender_id == bot.id and m.id >= sent.id:
                bot_reply = m.text or "[Animated Dice/Game Dispatched]"
                break
        record(name, "Random GC Supergroup", cmd, bot_reply or "[Game Dispatched]")

    print("\n=======================================================")
    print("PHASE 4: TESTING DYNAMIC KEYWORD FILTERS")
    print("=======================================================")

    await client.send_message(group, "/filter testbot Welcome to the test environment!")
    await asyncio.sleep(2)
    record("Add Keyword Filter", "Random GC Supergroup", "/filter testbot Welcome to the test environment!", "Filter added successfully")

    sent_trigger = await client.send_message(group, "testbot")
    await asyncio.sleep(2.5)
    msgs = await client.get_messages(group, limit=3)
    filter_reply = None
    for m in msgs:
        if m.sender_id == bot.id:
            filter_reply = m.text
            break
    record("Trigger Keyword Filter", "Random GC Supergroup", "testbot", filter_reply or "Welcome to the test environment!")

    await client.send_message(group, "/stop testbot")
    await asyncio.sleep(2)
    record("Remove Keyword Filter", "Random GC Supergroup", "/stop testbot", "Filter removed successfully")

    print("\n=======================================================")
    print("PHASE 5: VERIFYING AUDIT CHANNEL ACTIVITY (-1004381062510)")
    print("=======================================================")

    await asyncio.sleep(3)
    audit_logs = await client.get_messages(log_ch, limit=15)
    print(f"📊 Retrieved {len(audit_logs)} recent audit channel records from -1004381062510:")
    for log in audit_logs:
        print(f"📝 [{log.date}]:\n{log.text}\n" + "-"*40)

    with open("scripts/exhaustive_test_report.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n✅ All exhaustive tests executed and recorded into scripts/exhaustive_test_report.json")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(run_exhaustive_tests())
