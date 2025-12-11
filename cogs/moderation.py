
"""
Copyright (c) 2024 GN027C (GNBot)
Licensed under the Apache License 2.0.
Based on work by Krypton.
"""

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from datetime import timedelta

class Moderation(commands.Cog, name="moderation"):
    def __init__(self, bot) -> None:
        self.bot = bot
        # Context Menus
        self.ctx_menu_user_info = app_commands.ContextMenu(
            name="Mod: User Info",
            callback=self.context_user_info
        )
        self.ctx_menu_warn = app_commands.ContextMenu(
            name="Mod: Warn User",
            callback=self.context_warn_user
        )
        self.bot.tree.add_command(self.ctx_menu_user_info)
        self.bot.tree.add_command(self.ctx_menu_warn)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu_user_info.name, type=self.ctx_menu_user_info.type)
        self.bot.tree.remove_command(self.ctx_menu_warn.name, type=self.ctx_menu_warn.type)

    # --- Context Menu Callbacks ---
    async def context_user_info(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You do not have permission to use this.", ephemeral=True)
            return
            
        embed = discord.Embed(title=f"User Info: {user}", color=0x2b2d31)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="ID", value=user.id, inline=True)
        embed.add_field(name="Joined Discord", value=discord.utils.format_dt(user.created_at, style="R"), inline=True)
        embed.add_field(name="Joined Server", value=discord.utils.format_dt(user.joined_at, style="R"), inline=True)
        
        # Determine strict permissions or roles could go here
        roles = [r.mention for r in user.roles if r.name != "@everyone"]
        if roles:
            embed.add_field(name=f"Roles ({len(roles)})", value=", ".join(roles[:10]), inline=False)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def context_warn_user(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message("You do not have permission to warn members.", ephemeral=True)
            return
        
        # Opens a modal to enter reason
        await interaction.response.send_modal(WarnModal(self.bot, user))

    # --- Commands ---

    @commands.hybrid_command(
        name="kick",
        description="Kick a user out of the server.",
    )
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @app_commands.describe(user="The user that should be kicked.", reason="The reason for this kick.")
    async def kick(self, context: Context, user: discord.User, *, reason: str = "Not specified") -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        if member.top_role >= context.author.top_role:
            await context.send("You cannot kick someone with a higher or equal role.")
            return

        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                description=f"**{member}** was kicked by **{context.author}**!",
                color=0x2b2d31,
            )
            embed.add_field(name="Reason", value=reason)
            await context.send(embed=embed)
        except Exception as e:
            await context.send(f"Failed to kick user: {e}")

    @commands.hybrid_command(
        name="ban",
        description="Ban a user from the server.",
    )
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @app_commands.describe(user="The user that should be banned.", reason="The reason for this ban.")
    async def ban(self, context: Context, user: discord.User, *, reason: str = "Not specified") -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        if member.top_role >= context.author.top_role:
            await context.send("You cannot ban someone with a higher or equal role.")
            return

        try:
            await member.ban(reason=reason)
            embed = discord.Embed(
                description=f"**{member}** was banned by **{context.author}**!",
                color=0x2b2d31,
            )
            embed.add_field(name="Reason", value=reason)
            await context.send(embed=embed)
        except Exception as e:
            await context.send(f"Failed to ban user: {e}")

    @commands.hybrid_command(
        name="timeout",
        description="Timeout (Mute) a user.",
    )
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    @app_commands.describe(user="User to timeout", minutes="Duration in minutes", reason="Reason")
    async def timeout(self, context: Context, user: discord.Member, minutes: int, *, reason: str = "Not specified") -> None:
        if user.top_role >= context.author.top_role:
            await context.send("You cannot timeout someone with a higher or equal role.")
            return
        
        duration = timedelta(minutes=minutes)
        try:
            await user.timeout(duration, reason=reason)
            embed = discord.Embed(
                description=f"**{user}** has been timed out for {minutes} minutes.",
                color=0x2b2d31
            )
            embed.add_field(name="Reason", value=reason)
            await context.send(embed=embed)
        except Exception as e:
            await context.send(f"Failed to timeout: {e}")

    @commands.hybrid_command(
        name="purge",
        description="Delete messages with advanced filters.",
    )
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @app_commands.describe(
        amount="Amount of messages to check.",
        user="Only delete messages from this user.",
        contains="Only delete messages containing this text.",
        only_bots="Only delete bot messages."
    )
    async def purge(self, context: Context, amount: int, user: discord.User = None, contains: str = None, only_bots: bool = False) -> None:
        def check(m):
            # Don't delete the command message itself (if it exists)
            # But context.purge usually handles interaction differences, let's be safe
            if m.id == context.message.id:
                return False
                
            if user and m.author.id != user.id:
                return False
            if contains and contains not in m.content:
                return False
            if only_bots and not m.author.bot:
                return False
            return True

        if amount > 100:
            # Discord API limit for bulk delete
            await context.send("You can only purge up to 100 messages at a time due to Discord API limits.")
            return

        deleted = await context.channel.purge(limit=amount, check=check)
        
        embed = discord.Embed(
            description=f"Purged **{len(deleted)}** messages.",
            color=0x2b2d31,
        )
        if context.interaction:
             await context.interaction.response.send_message(embed=embed, ephemeral=True)
        else:
             msg = await context.send(embed=embed)
             await msg.delete(delay=5)

    @commands.hybrid_command(name="warnings", description="View warnings for a user")
    @commands.has_permissions(kick_members=True)
    async def warnings(self, context: Context, user: discord.User):
        warnings = await self.bot.database.get_warnings(user.id, context.guild.id)
        if not warnings:
            await context.send(f"{user.display_name} has no warnings.")
            return
        
        embed = discord.Embed(title=f"Warnings for {user.display_name}", color=0x2b2d31)
        for warn in warnings:
             # Using dictionary access as configured in DatabaseManager
             embed.add_field(
                 name=f"ID: {warn['id']} | Mod: <@{warn['moderator_id']}>",
                 value=f"Reason: {warn['reason']}\nDate: {warn['created_at']}",
                 inline=False
             )
        await context.send(embed=embed)

class WarnModal(discord.ui.Modal, title="Warn User"):
    reason = discord.ui.TextInput(
        label="Reason",
        placeholder="Enter the reason for warning...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=255
    )

    def __init__(self, bot, user: discord.Member):
        super().__init__()
        self.bot = bot
        self.user = user

    async def on_submit(self, interaction: discord.Interaction):
        # Save to DB
        warn_id = await self.bot.database.add_warn(
            self.user.id,
            interaction.guild.id,
            interaction.user.id,
            self.reason.value
        )
        
        embed = discord.Embed(
            title="User Warned",
            description=f"**{self.user}** has been warned.",
            color=0x2b2d31
        )
        embed.add_field(name="Reason", value=self.reason.value)
        embed.add_field(name="Warn ID", value=warn_id)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(Moderation(bot))
