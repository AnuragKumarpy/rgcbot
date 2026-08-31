import asyncio
import os
from telethon import TelegramClient

API_ID = 28102220
API_HASH = "c9ff5d60c4b80bf5f7de1092082207a5"
SESSION_PATH = "scripts/user_session"


async def sync_all_group_members():
    print("Connecting to Telegram client...")
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()

    group_id = -1003801913218
    group = await client.get_entity(group_id)
    print(f"Fetching participants for group: {group.title} ({group_id})...")
    participants = await client.get_participants(group, limit=5000)
    print(f"Fetched {len(participants)} total participants!")

    sql_lines = []
    for p in participants:
        if p.bot:
            continue
        u_id = p.id
        uname = f"'{p.username}'" if p.username else "NULL"
        fname = (p.first_name or "").replace("'", "''")
        lname = (p.last_name or "").replace("'", "''")

        sql_lines.append(
            f"INSERT INTO users (user_id, username, first_name, last_name, karma, coins, daily_streak, badges, is_afk, created_at, updated_at) "
            f"VALUES ({u_id}, {uname}, '{fname}', '{lname}', 0, 0, 0, '[]', false, NOW(), NOW()) "
            f"ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username, first_name = EXCLUDED.first_name;"
        )
        sql_lines.append(
            f"INSERT INTO group_members (chat_id, user_id, warnings_count, is_muted, is_banned, message_count, joined_at, last_active_at) "
            f"VALUES ({group_id}, {u_id}, 0, false, false, 0, NOW(), NOW()) "
            f"ON CONFLICT DO NOTHING;"
        )

    sql_file = "scripts/sync_members.sql"
    with open(sql_file, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_lines))

    print(f"Generated {len(sql_lines)} SQL statements in {sql_file}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(sync_all_group_members())
