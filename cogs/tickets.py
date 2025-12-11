
"""
Copyright (c) 2024 GN027C (GNBot)
Licensed under the Apache License 2.0.
Based on work by Krypton.
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Persistent view

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.green, custom_id="persistent_view:create_ticket", emoji="📩")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # ACK immediately
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Tickets")
        
        # Check permissions or create category logic could go here
        if not category:
            # Try to create category if not exists (requires perms)
            try:
                category = await guild.create_category("Tickets")
            except discord.Forbidden:
                await interaction.followup.send("Error: I need 'Manage Channels' permission to create the Tickets category.", ephemeral=True)
                return

        # Check if user already has a ticket
        ticket_channel_name = f"ticket-{interaction.user.name.lower()[:10]}"
        existing_channel = discord.utils.get(guild.text_channels, name=ticket_channel_name)
        if existing_channel:
            await interaction.followup.send(f"You already have a ticket open: {existing_channel.mention}", ephemeral=True)
            return

        # Create Channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        try:
            channel = await guild.create_text_channel(
                name=ticket_channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket for {interaction.user.id}"
            )
        except Exception as e:
            await interaction.followup.send(f"Failed to create ticket channel: {e}", ephemeral=True)
            return

        # Send controls to the new channel
        embed = discord.Embed(
            title=f"Ticket Support",
            description=f"Welcome {interaction.user.mention}. Support will be with you shortly.\nClick below to close this ticket.",
            color=0x2b2d31
        )
        await channel.send(content=f"{interaction.user.mention}", embed=embed, view=TicketControlView())
        
        await interaction.followup.send(f"Ticket created: {channel.mention}", ephemeral=True)

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="ticket_control:close", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing ticket in 5 seconds...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class Tickets(commands.Cog, name="tickets"):
    def __init__(self, bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        # Register the persistent view when Cog loads
        self.bot.add_view(TicketView())
        self.bot.add_view(TicketControlView())

    @commands.hybrid_command(name="ticketsetup", description="Setup the ticket panel.")
    @commands.has_permissions(administrator=True)
    async def ticket_setup(self, context: commands.Context) -> None:
        embed = discord.Embed(
            title="🎫 Support Tickets",
            description="Click the button below to open a support ticket.",
            color=0x2b2d31
        )
        await context.send(embed=embed, view=TicketView())
        
        # Ephemeral notification
        await context.send("Ticket panel sent!", ephemeral=True)

async def setup(bot) -> None:
    await bot.add_cog(Tickets(bot))
