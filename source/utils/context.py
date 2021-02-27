from discord.ext.commands import Context as _BaseContext

import json


class Context(_BaseContext):
    """A Custom Context for extra functionality."""

    async def guild_config(self):
        """Gets the config for the guild."""
        guild = await self.bot.db.fetch_guild(self.guild.id)

        if guild:
            return json.loads(guild["config"])
        return {}
