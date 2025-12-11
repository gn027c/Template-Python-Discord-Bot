
"""
Copyright (c) 2024 GN027C (GNBot)
Licensed under the Apache License 2.0.
Based on work by Krypton.
"""

import os
import platform
import random
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context

from core.logger import setup_logging
from core.config import config
from database import DatabaseManager

class GNBot(commands.Bot):
    def __init__(self) -> None:
        pass
        # Initialize Logger
        self.logger = setup_logging()
        self.config = config
        self.config.validate()

        # Database placeholder (will be implemented in Phase 2)
        self.database = None 

        # Intents setup
        intents = discord.Intents.default()
        intents.message_content = True # Required for some features
        # Enable other privileged intents if needed
        # intents.members = True 

        super().__init__(
            command_prefix=commands.when_mentioned_or(self.config.prefix),
            intents=intents,
            help_command=None,
        )

    async def init_db(self) -> None:
        self.logger.info("Initializing Database...")
        # Initialize DatabaseManager
        # Using a file based DB, path relative to project root
        db_path = f"{os.path.realpath(os.path.dirname(os.path.dirname(__file__)))}/database/database.db"
        self.database = DatabaseManager(db_path)
        
        # Connect and execute schema
        try:
            await self.database.connect()
            schema_path = f"{os.path.realpath(os.path.dirname(os.path.dirname(__file__)))}/database/schema.sql"
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = f.read()
                await self.database.connection.executescript(schema)
            self.logger.info("Database initialized and schema updated.")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")

    async def load_cogs(self) -> None:
        """
        Loads all cogs from the cogs directory.
        """
        cogs_dir = f"{os.path.realpath(os.path.dirname(os.path.dirname(__file__)))}/cogs"
        if not os.path.exists(cogs_dir):
            self.logger.warning(f"Cogs directory not found: {cogs_dir}")
            return

        for file in os.listdir(cogs_dir):
            if file.endswith(".py") and not file.startswith("__"):
                extension = file[:-3]
                try:
                    await self.load_extension(f"cogs.{extension}")
                    self.logger.info(f"Loaded extension '{extension}'")
                except Exception as e:
                    exception = f"{type(e).__name__}: {e}"
                    self.logger.error(
                        f"Failed to load extension {extension}\n{exception}"
                    )

    @tasks.loop(minutes=1.0)
    async def status_task(self) -> None:
        """
        Setup the game status task of the bot.
        """
        statuses = ["with GNBot Code", "with Users"]
        await self.change_presence(activity=discord.Game(random.choice(statuses)))

    @status_task.before_loop
    async def before_status_task(self) -> None:
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        """
        This will be executed when the bot starts.
        """
        self.logger.info(f"Logged in as {self.user.name}")
        self.logger.info(f"discord.py API version: {discord.__version__}")
        self.logger.info(f"Python version: {platform.python_version()}")
        self.logger.info(
            f"Running on: {platform.system()} {platform.release()} ({os.name})"
        )
        self.logger.info("-------------------")
        
        await self.init_db()
        await self.load_cogs()
        self.status_task.start()

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user or message.author.bot:
            return
        await self.process_commands(message)

    async def on_command_completion(self, context: Context) -> None:
        full_command_name = context.command.qualified_name
        split = full_command_name.split(" ")
        executed_command = str(split[0])
        self.logger.info(
            f"Executed {executed_command} command by {context.author} (ID: {context.author.id})"
        )

    async def on_command_error(self, context: Context, error) -> None:
        if hasattr(context.command, "on_error"):
            return

        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            embed = discord.Embed(
                description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description="You are missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to execute this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                description="I am missing the permission(s) `"
                + ", ".join(error.missing_permissions)
                + "` to fully perform this command!",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Error!",
                description=str(error).capitalize(),
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        else:
            raise error
