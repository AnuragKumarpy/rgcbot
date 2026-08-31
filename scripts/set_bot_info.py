import asyncio
from src.core.bot import create_bot
from src.core.logging import setup_logging
from src.services.bot_metadata_service import setup_bot_metadata


async def main():
    setup_logging()
    bot = create_bot()
    print("Setting up bot metadata with Telegram Bot API...")
    await setup_bot_metadata(bot)
    me = await bot.get_me()
    desc = await bot.get_my_description()
    short_desc = await bot.get_my_short_description()
    print(f"✅ Successfully configured @{me.username} ({me.first_name})")
    print(f"Short Description: {short_desc.short_description}")
    print("Description set successfully!")
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
