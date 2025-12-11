
"""
Copyright (c) 2024 GN027C (GNBot)
Licensed under the Apache License 2.0.
Based on work by Krypton.
"""

"""
GNBot - Custom Discord Bot
Entry Point
"""
import asyncio
import os
import sys

# Ensure the core module is accessible found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.bot import GNBot
from core.config import config

async def main():
    bot = GNBot()
    # Validate token existence before running
    if not config.token:
        print("Error: TOKEN not found in .env file.")
        return
    
    async with bot:
        await bot.start(config.token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # User pressed Ctrl+C
        pass
    except Exception as e:
        print(f"Fatal Error: {e}")
