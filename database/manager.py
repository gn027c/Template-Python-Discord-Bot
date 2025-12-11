
"""
Copyright (c) 2024 GN027C (GNBot)
Licensed under the Apache License 2.0.
Based on work by Krypton.
"""

import aiosqlite
import os

class DatabaseManager:
    """
    Class to manage database interactions for GNBot.
    Handles connection lifecycle and common queries.
    """
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.connection = None

    async def connect(self):
        """Initializes the database connection."""
        if not self.connection:
            self.connection = await aiosqlite.connect(self.database_path)
            self.connection.row_factory = aiosqlite.Row 
            await self.connection.execute("PRAGMA foreign_keys = ON") 

    async def close(self):
        """Closes the database connection."""
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def execute(self, query: str, parameters: tuple = ()) -> None:
        """Executes a query that changes data (INSERT, UPDATE, DELETE)."""
        await self.connect() 
        await self.connection.execute(query, parameters)
        await self.connection.commit()

    async def fetch_one(self, query: str, parameters: tuple = ()) -> aiosqlite.Row:
        """Executes a query and returns one result."""
        await self.connect()
        async with self.connection.execute(query, parameters) as cursor:
            return await cursor.fetchone()

    async def fetch_all(self, query: str, parameters: tuple = ()) -> list:
        """Executes a query and returns all results."""
        await self.connect()
        async with self.connection.execute(query, parameters) as cursor:
            return await cursor.fetchall()
    
    # --- Helper Methods ---
    
    # WARNS
    async def add_warn(self, user_id: int, server_id: int, moderator_id: int, reason: str) -> int:
        await self.execute(
            "INSERT INTO warns(user_id, server_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
            (user_id, server_id, moderator_id, reason),
        )
        res = await self.fetch_one("SELECT last_insert_rowid() as id")
        return res['id']

    async def remove_warn(self, warn_id: int) -> None:
        await self.execute("DELETE FROM warns WHERE id=?", (warn_id,))

    async def get_warnings(self, user_id: int, server_id: int) -> list:
        return await self.fetch_all(
            "SELECT * FROM warns WHERE user_id=? AND server_id=?",
            (user_id, server_id),
        )

    # ECONOMY
    async def get_balance(self, user_id: int, server_id: int) -> dict:
        result = await self.fetch_one(
            "SELECT wallet, bank FROM economy_users WHERE user_id=? AND server_id=?",
            (user_id, server_id)
        )
        if result:
            return dict(result)
        else:
            await self.execute(
                "INSERT INTO economy_users(user_id, server_id) VALUES (?, ?)",
                (user_id, server_id)
            )
            return {"wallet": 0, "bank": 0}

    async def update_wallet(self, user_id: int, server_id: int, amount: int) -> None:
        await self.get_balance(user_id, server_id) 
        await self.execute(
            "UPDATE economy_users SET wallet = wallet + ? WHERE user_id=? AND server_id=?",
            (amount, user_id, server_id)
        )

    # LEVELING
    async def get_level_data(self, user_id: int, server_id: int) -> dict:
        result = await self.fetch_one(
            "SELECT xp, level, last_message FROM levels WHERE user_id=? AND server_id=?",
            (user_id, server_id)
        )
        if result:
            return dict(result)
        return None

    async def insert_level_user(self, user_id: int, server_id: int):
        await self.execute(
            "INSERT OR IGNORE INTO levels(user_id, server_id) VALUES (?, ?)",
            (user_id, server_id)
        )
        
    # SETTINGS (NEW)
    async def get_guild_settings(self, server_id: int) -> dict:
        result = await self.fetch_one("SELECT * FROM guild_settings WHERE server_id=?", (server_id,))
        if result:
            return dict(result)
        else:
            # Defaults
            await self.execute("INSERT INTO guild_settings(server_id) VALUES (?)", (server_id,))
            return {"xp_rate_text": 1, "xp_rate_voice": 10, "level_difficulty": 100}

    async def update_guild_setting(self, server_id: int, setting: str, value: int):
        # Valid settings check could be here
        await self.execute(f"UPDATE guild_settings SET {setting} = ? WHERE server_id=?", (value, server_id))
