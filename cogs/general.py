
"""
Copyright (c) 2024 GN027C (GNBot)
Licensed under the Apache License 2.0.
Based on work by Krypton.
"""

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

class General(commands.Cog, name="general"):
    def __init__(self, bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="help", description="List all visible commands."
    )
    async def help(self, context: Context) -> None:
        """
        Displays a list of available commands grouped by Cog.
        """
        embed = discord.Embed(
            title="Help Menu",
            description="Here are the commands you can use:",
            color=0x2b2d31 # Discord dark theme color
        )
        
        for cog_name in self.bot.cogs:
            # Skip owner-only cogs if the user is not an owner (simple check)
            # You might want to enhance this permission check later
            if cog_name.lower() == "owner" and not await self.bot.is_owner(context.author):
                continue

            cog = self.bot.get_cog(cog_name)
            commands_list = []
            for command in cog.walk_commands():
                # Filter out commands that have parents (subcommands) to avoid duplicates if you only want top-level
                # Or keep them if you want flat list. Here we list parent commands primarily.
                if command.parent is None:
                    commands_list.append(command)
                
            data = []
            for command in commands_list:
                if command.hidden:
                    continue
                description = command.description.partition("\n")[0]
                data.append(f"**/{command.name}** - {description}")
            
            if data:
                help_text = "\n".join(data)
                embed.add_field(
                    name=cog_name.capitalize(), value=help_text, inline=False
                )
        
        embed.set_footer(text=f"Requested by {context.author}")
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="ping",
        description="Check if the bot is alive and view latency.",
    )
    async def ping(self, context: Context) -> None:
        """
        Check latency.
        """
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latency: **{round(self.bot.latency * 1000)}ms**",
            color=0x2b2d31,
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="botinfo",
        description="Get information about GNBot.",
    )
    async def botinfo(self, context: Context) -> None:
        """
        Displays current bot status and info.
        """
        embed = discord.Embed(
            description="Custom Discord Bot - GNBot",
            color=0x2b2d31,
        )
        embed.set_author(name="Bot Information")
        embed.add_field(
            name="Python Version:", value=f"{discord.utils.sys.version.split(' ')[0]}", inline=True
        )
        embed.add_field(
            name="Discord.py Version:", value=f"{discord.__version__}", inline=True
        )
        embed.set_footer(text=f"Requested by {context.author}")
        await context.send(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(General(bot))
