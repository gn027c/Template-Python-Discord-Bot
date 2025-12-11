
"""
Copyright (c) 2024 GN027C (GNBot)
Licensed under the Apache License 2.0.
Based on work by Krypton.
"""

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands
import random

# --- UI COMPONENTS FOR SHOP MANAGEMENT ---

# --- MODALS ---

class AddItemModal(discord.ui.Modal, title="Add New Item"):
    emoji_input = discord.ui.TextInput(label="Emoji", placeholder="Item Emoji", required=True)
    price_input = discord.ui.TextInput(label="Price", placeholder="Item Price (e.g. 1000)", required=True)
    name_input = discord.ui.TextInput(label="Name", placeholder="Item Name", style=discord.TextStyle.short, required=True)

    def __init__(self, bot, view_ref):
        super().__init__()
        self.bot = bot
        self.view_ref = view_ref

    async def on_submit(self, interaction: discord.Interaction):
        try:
            price = int(self.price_input.value)
        except ValueError:
            await interaction.response.send_message("Price must be a number.", ephemeral=True)
            return

        await self.bot.database.execute(
            "INSERT INTO shop_items(server_id, name, price, description) VALUES (?, ?, ?, ?)",
            (interaction.guild.id, self.emoji_input.value, price, self.name_input.value)
        )
        
        await interaction.response.send_message(f"✅ Added **{self.name_input.value}** {self.emoji_input.value}.", ephemeral=True)
        # We should refresh the select menu in the parent view
        # But select menus are static in constructor. We'd need to re-send the view or update it.
        # For simplicity, we ask user to re-run manage or we assume they will.

class EditItemModal(discord.ui.Modal):
    def __init__(self, bot, item_id, current_name, current_price, current_desc, view):
        super().__init__(title=f"Edit Item ID: {item_id}")
        self.bot = bot
        self.item_id = item_id
        self.view_ref = view # Reference to parent view to update it
        
        self.name_input = discord.ui.TextInput(label="Name", default=current_name, required=True)
        self.price_input = discord.ui.TextInput(label="Price", default=str(current_price), required=True)
        self.desc_input = discord.ui.TextInput(label="Description", default=current_desc, style=discord.TextStyle.paragraph, required=False)
        
        self.add_item(self.name_input)
        self.add_item(self.price_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_price = int(self.price_input.value)
        except ValueError:
            await interaction.response.send_message("Price must be a number.", ephemeral=True)
            return

        await self.bot.database.execute(
            "UPDATE shop_items SET name=?, price=?, description=? WHERE item_id=?",
            (self.name_input.value, new_price, self.desc_input.value, self.item_id)
        )
        await interaction.response.send_message(f"✅ Item `{self.item_id}` updated.", ephemeral=True)
        # Refresh the parent view if possible (requires re-rendering menu)

class ShopSelect(discord.ui.Select):
    def __init__(self, items):
        options = []
        if items:
            for item in items[:25]: # Limit 25 for Discord UI
                options.append(discord.SelectOption(
                    label=item['name'],
                    description=f"${item['price']} - ID: {item['item_id']}",
                    value=str(item['item_id'])
                ))
        else:
            options.append(discord.SelectOption(label="No items", value="none", description="Shop is empty"))

        super().__init__(placeholder="Select an item to manage...", min_values=1, max_values=1, options=options, disabled=(not items))

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("There are no items to select.", ephemeral=True)
            return
            
        item_id = int(self.values[0])
        # Fetch fresh data
        item = await self.view.bot.database.fetch_one("SELECT * FROM shop_items WHERE item_id=?", (item_id,))
        
        if not item:
            await interaction.response.send_message("Item no longer exists.", ephemeral=True)
            return

        # Enable buttons and store current selection
        self.view.current_item = dict(item)
        self.view.enable_buttons()
        
        embed = discord.Embed(title=f"Selected: {item['name']}", color=0x3498db)
        embed.add_field(name="Price", value=f"${item['price']}")
        embed.add_field(name="Description", value=item['description'])
        embed.add_field(name="ID", value=str(item['item_id']))
        
        await interaction.response.edit_message(embed=embed, view=self.view)

class ShopManageView(discord.ui.View):
    def __init__(self, bot, items):
        super().__init__(timeout=180)
        self.bot = bot
        self.items = items
        self.current_item = None
        
        self.add_item(ShopSelect(items))
        
        # Add Item Button (Always visible)
        self.btn_add = discord.ui.Button(label="Add Item", style=discord.ButtonStyle.success, emoji="➕")
        self.btn_add.callback = self.on_add
        self.add_item(self.btn_add)

        # Edit/Delete Buttons (Initially disabled)
        self.btn_edit = discord.ui.Button(label="Edit", style=discord.ButtonStyle.primary, disabled=True)
        self.btn_edit.callback = self.on_edit
        self.add_item(self.btn_edit)

        self.btn_delete = discord.ui.Button(label="Delete", style=discord.ButtonStyle.danger, disabled=True)
        self.btn_delete.callback = self.on_delete
        self.add_item(self.btn_delete)

    def enable_buttons(self):
        self.btn_edit.disabled = False
        self.btn_delete.disabled = False

    async def on_add(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddItemModal(self.bot, self))

    async def on_edit(self, interaction: discord.Interaction):
        if not self.current_item: return
        await interaction.response.send_modal(EditItemModal(
            self.bot, 
            self.current_item['item_id'],
            self.current_item['name'],
            self.current_item['price'],
            self.current_item['description'],
            self
        ))

    async def on_delete(self, interaction: discord.Interaction):
        if not self.current_item: return
        
        await self.bot.database.execute("DELETE FROM shop_items WHERE item_id=?", (self.current_item['item_id'],))
        await interaction.response.send_message(f"❌ Item `{self.current_item['name']}` deleted.", ephemeral=True)
        self.stop() # Stop view as list is now invalid

# --- MAIN COG ---

class Economy(commands.Cog, name="economy"):
    def __init__(self, bot) -> None:
        self.bot = bot

    async def get_user_balance(self, user_id: int, guild_id: int):
        return await self.bot.database.get_balance(user_id, guild_id)

    # --- BASIC ECONOMY COMMANDS ---
    @commands.hybrid_command(name="balance", description="Check your wallet and bank balance.")
    @app_commands.describe(user="The user to check balance for (default: yourself).")
    async def balance(self, context: commands.Context, user: discord.User = None) -> None:
        target = user or context.author
        bal = await self.get_user_balance(target.id, context.guild.id)
        
        embed = discord.Embed(title=f"Balance: {target.display_name}", color=0xffd700) 
        embed.add_field(name="💳 Wallet", value=f"${bal['wallet']:,}", inline=True)
        embed.add_field(name="🏦 Bank", value=f"${bal['bank']:,}", inline=True)
        embed.add_field(name="💰 Net Worth", value=f"${bal['wallet'] + bal['bank']:,}", inline=False)
        
        await context.send(embed=embed)

    @commands.hybrid_command(name="daily", description="Collect your daily income.")
    async def daily(self, context: commands.Context) -> None:
        amount = 1000
        await self.bot.database.update_wallet(context.author.id, context.guild.id, amount)
        embed = discord.Embed(description=f"✅ You collected your daily **${amount}**!", color=0x2b2d31)
        await context.send(embed=embed)

    @commands.hybrid_command(name="work", description="Work to earn money.")
    @commands.cooldown(1, 3600, commands.BucketType.user) 
    async def work(self, context: commands.Context) -> None:
        jobs = [("Developer", 500, 1000), ("Artist", 300, 800), ("Streamer", 100, 2000)]
        job_name, min_pay, max_pay = random.choice(jobs)
        earnings = random.randint(min_pay, max_pay)
        
        await self.bot.database.update_wallet(context.author.id, context.guild.id, earnings)
        embed = discord.Embed(description=f"🔨 You worked as a **{job_name}** and earned **${earnings}**.", color=0x2b2d31)
        await context.send(embed=embed)
        
    @work.error
    async def work_error(self, context, error):
        if isinstance(error, commands.CommandOnCooldown):
            minutes = round(error.retry_after / 60)
            await context.send(f"Wait {minutes} minutes before working again!", ephemeral=True)

    @commands.hybrid_command(name="deposit", description="Deposit money into your bank.")
    async def deposit(self, context: commands.Context, amount: str) -> None:
        bal = await self.get_user_balance(context.author.id, context.guild.id)
        if amount.lower() == "all":
            deposit_amount = bal['wallet']
        else:
            try:
                deposit_amount = int(amount)
            except ValueError:
                await context.send("Invalid number.", ephemeral=True)
                return
        
        if deposit_amount > bal['wallet'] or deposit_amount <= 0:
            await context.send("Invalid amount.", ephemeral=True)
            return

        await self.bot.database.execute("UPDATE economy_users SET wallet = wallet - ?, bank = bank + ? WHERE user_id=? AND server_id=?", (deposit_amount, deposit_amount, context.author.id, context.guild.id))
        await context.send(f"✅ Deposited **${deposit_amount}**.")

    @commands.hybrid_command(name="withdraw", description="Withdraw money from your bank.")
    async def withdraw(self, context: commands.Context, amount: str) -> None:
        bal = await self.get_user_balance(context.author.id, context.guild.id)
        if amount.lower() == "all":
            amt = bal['bank']
        else:
            try:
                amt = int(amount)
            except ValueError:
                await context.send("Invalid number.", ephemeral=True)
                return

        if amt > bal['bank'] or amt <= 0:
            await context.send("Invalid amount.", ephemeral=True)
            return

        await self.bot.database.execute("UPDATE economy_users SET wallet = wallet + ?, bank = bank - ? WHERE user_id=? AND server_id=?", (amt, amt, context.author.id, context.guild.id))
        await context.send(f"✅ Withdrew **${amt}**.")

    # --- SHOP COMMANDS ---

    @commands.hybrid_group(name="shop", description="Shop commands.", invoke_without_command=True)
    async def shop(self, context: Context) -> None:
        if context.invoked_subcommand is None:
            embed = discord.Embed(title="Shop Commands", description="`/shop items` - View Items\n`/shop manage` - Manage Shop (Admin)", color=0x2b2d31)
            await context.send(embed=embed)

    @shop.command(name="items", description="View available items.")
    async def shop_items(self, context: Context) -> None:
        items = await self.bot.database.fetch_all("SELECT * FROM shop_items WHERE server_id=?", (context.guild.id,))
        if not items:
            await context.send("Shop is empty.")
            return
        embed = discord.Embed(title="🛒 Shop", color=0x2b2d31)
        for item in items:
            embed.add_field(name=f"{item['name']} - ${item['price']:,}", value=f"{item['description']}\nID: `{item['item_id']}`", inline=False)
        await context.send(embed=embed)

    @shop.command(name="manage", description="Admin: Manage shop items (Add/Edit/Delete).")
    @commands.has_permissions(administrator=True)
    async def shop_manage(self, context: Context) -> None:
        items = await self.bot.database.fetch_all("SELECT * FROM shop_items WHERE server_id=?", (context.guild.id,))
        # Allow opening manager even if empty to ADD items
            
        view = ShopManageView(self.bot, items)
        embed = discord.Embed(title="🔧 Shop Manager", description="Use the controls below to manage the shop.", color=0x2b2d31)
        await context.send(embed=embed, view=view)


    @commands.hybrid_command(name="buy", description="Buy an item.")
    async def buy(self, context: Context, item_id: int) -> None:
        # Same logic as before, abbreviated for space
        item = await self.bot.database.fetch_one("SELECT * FROM shop_items WHERE item_id=? AND server_id=?", (item_id, context.guild.id))
        if not item:
            await context.send("Item not found.", ephemeral=True)
            return
        bal = await self.get_user_balance(context.author.id, context.guild.id)
        if bal['wallet'] < item['price']:
            await context.send("Not enough money.", ephemeral=True)
            return

        await self.bot.database.execute("UPDATE economy_users SET wallet = wallet - ? WHERE user_id=? AND server_id=?", (item['price'], context.author.id, context.guild.id))
        
        existing = await self.bot.database.fetch_one("SELECT id FROM inventory WHERE user_id=? AND item_id=?", (context.author.id, item_id))
        if existing:
             await self.bot.database.execute("UPDATE inventory SET quantity = quantity + 1 WHERE id=?", (existing['id'],))
        else:
             await self.bot.database.execute("INSERT INTO inventory(user_id, server_id, item_id) VALUES (?, ?, ?)", (context.author.id, context.guild.id, item_id))
        
        await context.send(f"🛍️ Bought **{item['name']}**!")

    @commands.hybrid_command(name="inventory", description="View your inventory.")
    async def inventory(self, context: Context) -> None:
        inv = await self.bot.database.fetch_all("SELECT i.quantity, s.name, s.description FROM inventory i JOIN shop_items s ON i.item_id = s.item_id WHERE i.user_id=? AND i.server_id=?", (context.author.id, context.guild.id))
        if not inv:
            await context.send("Empty inventory.")
            return
        embed = discord.Embed(title=f"Inventory: {context.author.display_name}", color=0x2b2d31)
        for item in inv:
            embed.add_field(name=f"{item['name']} (x{item['quantity']})", value=item['description'], inline=False)
        await context.send(embed=embed)

async def setup(bot) -> None:
    await bot.add_cog(Economy(bot))
