from asyncpg import create_pool
from os import getenv
from json import dumps


class Database:
    """A database interface for the bot to connect to Postgres."""

    def __init__(self):
        self.guilds = {}
        self.users = {}

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

    async def fetch_user(self, id: int):
        if id in self.users:
            return self.users[id]

        data = await self.fetchrow("SELECT * FROM Users WHERE id = $1;", id)
        self.users[id] = data
        return data
