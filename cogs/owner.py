
"""
Copyright (c) 2024 GN027C (GNBot)
Licensed under the Apache License 2.0.
Based on work by Krypton.
"""

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

class Owner(commands.Cog, name="owner"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.command(name="sync", description="Synchonizes the slash commands.")
    @commands.is_owner()
    async def sync(self, context: Context, scope: str = "global") -> None:
        """
        Synchronizes Slash Commands.
        Scope: 'global' or 'guild'
        """
        if scope == "global":
            await context.bot.tree.sync()
            msg = "Global sync complete."
        elif scope == "guild":
            context.bot.tree.copy_global_to(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            msg = "Guild sync complete."
        else:
            msg = "Invalid scope. Use `global` or `guild`."

        # Simple reply instead of complex embeds for owner tools
        await context.send(msg)

    @commands.command(name="load", description="Load a cog.")
    @commands.is_owner()
    async def load(self, context: Context, cog: str) -> None:
        try:
            await self.bot.load_extension(f"cogs.{cog}")
            await context.send(f"Loaded: `{cog}`")
        except Exception as e:
            await context.send(f"Error loading `{cog}`: {e}")

    @commands.command(name="unload", description="Unload a cog.")
    @commands.is_owner()
    async def unload(self, context: Context, cog: str) -> None:
        try:
            await self.bot.unload_extension(f"cogs.{cog}")
            await context.send(f"Unloaded: `{cog}`")
        except Exception as e:
            await context.send(f"Error unloading `{cog}`: {e}")

    @commands.command(name="reload", description="Reload a cog.")
    @commands.is_owner()
    async def reload(self, context: Context, cog: str) -> None:
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await context.send(f"Reloaded: `{cog}`")
        except Exception as e:
            await context.send(f"Error reloading `{cog}`: {e}")

    @commands.command(name="shutdown", description="Shuts down the bot.")
    @commands.is_owner()
    async def shutdown(self, context: Context) -> None:
        await context.send("Shutting down...")
        await self.bot.close()

async def setup(bot) -> None:
    await bot.add_cog(Owner(bot))
