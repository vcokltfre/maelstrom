from asyncpg import create_pool
from os import getenv
from json import dumps


class Database:
    """A database interface for the bot to connect to Postgres."""

    def __init__(self):
        self.guilds = {}
        self.users = {}
        self.banned = set()

    async def setup(self):
        self.pool = await create_pool(
            host=getenv("DB_HOST", "127.0.0.1"),
            port=getenv("DB_PORT", 5432),
            database=getenv("DB_DATABASE", "maelstrom"),
            user=getenv("DB_USER", "root"),
            password=getenv("DB_PASS", "password"),
        )

    async def execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            await conn.execute(query, *args)

    async def fetchrow(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def create_guild(self, id: int, prefix: str = "!", config: dict = {}):
        await self.execute(
            "INSERT INTO Guilds (id, prefix, config) VALUES ($1, $2, $3);", id, prefix, dumps(config)
        )

    async def update_guild_prefix(self, id: int, prefix: str):
        if not await self.fetch_guild(id):
            return await self.create_guild(id, prefix)

        if id in self.guilds:
            del self.guilds[id]
        await self.execute("UPDATE Guilds SET prefix = $1 WHERE id = $2;", prefix, id)

    async def update_guild_config(self, id: int, config: dict):
        if not await self.fetch_guild(id):
            await self.create_guild(id)

        if id in self.guilds:
            del self.guilds[id]
        await self.execute("UPDATE Guilds SET config = $1 WHERE id = $2;", dumps(config), id)

    async def fetch_guild(self, id: int):
        if id in self.guilds:
            return self.guilds[id]

        data = await self.fetchrow("SELECT * FROM Guilds WHERE id = $1;", id)
        self.guilds[id] = data
        return data

    async def create_user(self, id: int, guild_id: int, xp: int = 0):
        await self.execute("INSERT INTO Users (id, guildid, xp) VALUES ($1, $2, $3);", id, guild_id, xp)

    async def add_xp(self, id: int, guild_id: int, xp: int = 0):
        await self.execute("UPDATE Users SET xp = xp + $3 WHERE id = $1 AND guildid = $2;", id, guild_id, xp)
        if id in self.users:
            del self.users[id]

    async def fetch_user(self, id: int, guild_id: int):
        bucket = f"{id}/{guild_id}"
        if bucket in self.users:
            return self.users[bucket]

        data = await self.fetchrow("SELECT * FROM Users WHERE id = $1 AND guildid = $2;", id, guild_id)
        self.users[bucket] = data
        return data

    async def fetch_top_users(self, guild_id: int, count: int = 15):
        return await self.fetch("SELECT * FROM Users WHERE guildid = $1 ORDER BY xp DESC LIMIT $2;", guild_id, count)

    async def get_rank(self, id: int, guild_id: int):
        return await self.fetchrow("SELECT rank FROM (SELECT id, RANK () OVER (ORDER BY xp) FROM Users WHERE guildid = $1) as ranks WHERE id = $2;", guild_id, id)

    async def user_is_banned(self, id: int) -> bool:
        if id in self.banned:
            return True
        users = await self.fetch("SELECT * FROM Users WHERE id = $1;", id)

        for user in users:
            if user["banned"]:
                self.banned.add(id)
                return True

        return False

    async def clear_guild(self, id: int):
        await self.execute("DELETE FROM Users WHERE guildid = $1;", id)

    async def add_users(self, users: list):
        async with self.pool.acquire() as conn:
            await conn.executemany("INSERT INTO Users VALUES ($1, $2, $3, $4, $5);", users)
