
"""
Copyright (c) 2024 GN027C (GNBot)
Licensed under the Apache License 2.0.
Based on work by Krypton.
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Context
from datetime import datetime
import random
import time

class Leveling(commands.Cog, name="leveling"):
    def __init__(self, bot) -> None:
        self.bot = bot
        self._cd = commands.CooldownMapping.from_cooldown(1.0, 60.0, commands.BucketType.user) 
        self._voice_sessions = {} # {user_id: timestamp_joined}

    def get_ratelimit(self, message: discord.Message):
        bucket = self._cd.get_bucket(message)
        return bucket.update_rate_limit()

    async def add_xp(self, user_id: int, guild_id: int, xp_amount: int):
        data = await self.bot.database.get_level_data(user_id, guild_id)
        settings = await self.bot.database.get_guild_settings(guild_id)
        
        difficulty = settings['level_difficulty'] # Default 100

        if not data:
            await self.bot.database.insert_level_user(user_id, guild_id)
            current_xp = 0
            current_level = 0
        else:
            current_xp = data['xp']
            current_level = data['level']

        new_xp = current_xp + xp_amount
        
        # Formula: XP = difficulty * Level^2
        # Reverse: Level = sqrt(XP / difficulty)
        new_level = int((new_xp / difficulty) ** 0.5)

        if new_level > current_level:
             await self.bot.database.execute(
                "UPDATE levels SET xp=?, level=? WHERE user_id=? AND server_id=?",
                (new_xp, new_level, user_id, guild_id)
            )
             return new_level
        else:
            await self.bot.database.execute(
                "UPDATE levels SET xp=? WHERE user_id=? AND server_id=?",
                (new_xp, user_id, guild_id)
            )
            return None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        retry_after = self.get_ratelimit(message)
        if retry_after:
            return 

        # Get Text Multiplier
        settings = await self.bot.database.get_guild_settings(message.guild.id)
        multiplier = settings['xp_rate_text']

        xp_gain = random.randint(15, 25) * multiplier
        new_level = await self.add_xp(message.author.id, message.guild.id, xp_gain)
        
        if new_level:
            await message.channel.send(f"🎉 {message.author.mention} reached **Level {new_level}**!")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot: 
            return

        now = time.time()
        
        # Case 1: Joined a channel (and wasn't in one before)
        if before.channel is None and after.channel is not None:
             self._voice_sessions[member.id] = now
        
        # Case 2: Left a channel (and isn't in one anymore)
        elif before.channel is not None and after.channel is None:
            if member.id in self._voice_sessions:
                joined_at = self._voice_sessions.pop(member.id)
                duration_seconds = now - joined_at
                
                # Minimum 1 minute to get XP
                if duration_seconds > 60:
                     minutes = int(duration_seconds / 60)
                     settings = await self.bot.database.get_guild_settings(member.guild.id)
                     xp_per_min = settings['xp_rate_voice']
                     
                     xp_gain = minutes * xp_per_min
                     new_level = await self.add_xp(member.id, member.guild.id, xp_gain)
                     
                     # Optional: Notify in system channel or DM
                     # if new_level: ...

        # Case 3: Switched channels (Treat as continuous or restart logic depending on preference)
        # Here we treat it as continuous, so we do nothing unless they disconnect.
        pass

    @commands.hybrid_command(name="rank", description="Check your rank and XP.")
    async def rank(self, context: Context, user: discord.User = None) -> None:
        target = user or context.author
        data = await self.bot.database.get_level_data(target.id, context.guild.id)
        settings = await self.bot.database.get_guild_settings(context.guild.id)
        difficulty = settings['level_difficulty']
        
        if not data:
            await context.send("User has no XP yet.")
            return
            
        xp = data['xp']
        level = data['level']
        next_level_xp = difficulty * ((level + 1) ** 2)
        
        embed = discord.Embed(title=f"Rank: {target.display_name}", color=0x2b2d31)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="XP", value=f"{xp} / {next_level_xp}", inline=True)
        
        percent = min((xp / next_level_xp), 1.0)
        filled = int(percent * 10)
        progressBar = "🟦" * filled + "⬜" * (10 - filled)
        embed.add_field(name="Progress", value=progressBar, inline=False)
        
        await context.send(embed=embed)

    @commands.hybrid_command(name="leaderboard", description="View the top XP leaders.")
    async def leaderboard(self, context: Context) -> None:
        results = await self.bot.database.fetch_all(
            "SELECT user_id, level, xp FROM levels WHERE server_id=? ORDER BY xp DESC LIMIT 10",
            (context.guild.id,)
        )
        
        if not results:
            await context.send("No leveled users yet.")
            return
            
        embed = discord.Embed(title="🏆 Server Leaderboard", color=0xD4AF37) # Gold
        desc = ""
        for i, row in enumerate(results, 1):
            user_id = int(row['user_id'])
            user = context.guild.get_member(user_id)
            
            if not user:
                # Try to fetch if not in cache
                try:
                    user = await context.guild.fetch_member(user_id)
                except:
                    pass
            
            # Use mention if possible, otherwise Name, otherwise ID
            display_text = user.mention if user else f"User <@{user_id}>"
            
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
            desc += f"{medal} {display_text}\nLevel {row['level']} • {row['xp']:,} XP\n\n"
            
        embed.description = desc
        await context.send(embed=embed)

    @commands.hybrid_group(name="xp", description="Manage Leveling settings.")
    @commands.has_permissions(administrator=True)
    async def xp(self, context: Context) -> None:
        if context.invoked_subcommand is None:
             await context.send_help("xp")

    @xp.command(name="set", description="Set a user's XP directly.")
    async def xp_set(self, context: Context, user: discord.User, amount: int) -> None:
        await self.bot.database.insert_level_user(user.id, context.guild.id) # Ensure exists
        # Recalculate level based on new XP
        settings = await self.bot.database.get_guild_settings(context.guild.id)
        difficulty = settings['level_difficulty']
        new_level = int((amount / difficulty) ** 0.5)
        
        await self.bot.database.execute(
            "UPDATE levels SET xp=?, level=? WHERE user_id=? AND server_id=?",
             (amount, new_level, user.id, context.guild.id)
        )
        await context.send(f"✅ Set {user.mention}'s XP to {amount} (Level {new_level}).")

    @xp.command(name="reset", description="Reset a user's XP to 0.")
    async def xp_reset(self, context: Context, user: discord.User) -> None:
        await self.bot.database.execute(
            "UPDATE levels SET xp=0, level=0 WHERE user_id=? AND server_id=?",
             (user.id, context.guild.id)
        )
        await context.send(f"✅ Reset {user.mention}'s XP.")

    @xp.command(name="settings", description="Configure XP rates.")
    @app_commands.describe(
        text_rate="Multiplier for text XP (Default: 1)",
        voice_rate="XP per minute in voice (Default: 10)",
        difficulty="Base XP for Level 1 (Default: 100)"
    )
    async def xp_settings(self, context: Context, text_rate: int = None, voice_rate: int = None, difficulty: int = None) -> None:
        current = await self.bot.database.get_guild_settings(context.guild.id)
        
        changes = []
        if text_rate:
            await self.bot.database.update_guild_setting(context.guild.id, "xp_rate_text", text_rate)
            changes.append(f"Text Rate: {current['xp_rate_text']} -> {text_rate}")
        if voice_rate:
             await self.bot.database.update_guild_setting(context.guild.id, "xp_rate_voice", voice_rate)
             changes.append(f"Voice Rate: {current['xp_rate_voice']} -> {voice_rate}")
        if difficulty:
             await self.bot.database.update_guild_setting(context.guild.id, "level_difficulty", difficulty)
             changes.append(f"Difficulty: {current['level_difficulty']} -> {difficulty}")
             
        if not changes:
            embed = discord.Embed(title="Current XP Settings", color=0x2b2d31)
            embed.add_field(name="Text Multiplier", value=current['xp_rate_text'])
            embed.add_field(name="Voice XP/Min", value=current['xp_rate_voice'])
            embed.add_field(name="Difficulty Base", value=current['level_difficulty'])
            await context.send(embed=embed)
        else:
            await context.send("✅ Updated Settings:\n" + "\n".join(changes))

async def setup(bot) -> None:
    await bot.add_cog(Leveling(bot))
