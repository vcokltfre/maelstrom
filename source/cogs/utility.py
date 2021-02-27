from discord.ext import commands
from typing import Optional

from source import Bot
from source.utils.checks import not_banned


class Utility(commands.Cog):
    """A set of utility commands for Maelstrom."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="prefix")
    @commands.check_any(commands.has_guild_permissions(manage_guild=True), commands.is_owner())
    @commands.guild_only()
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.member)
    @not_banned()
    async def prefix(self, ctx: commands.Context, *, new: Optional[str]):
        wording = "updated" if new else "reset"
        prefix = new or "!"

        if len(prefix) > 64:
            return await ctx.send("Your prefix can't be longer than 64 characters.")

        await self.bot.db.update_guild_prefix(ctx.guild.id, prefix)

        await ctx.send(f"Your prefix for this server has been {wording} to: `{prefix}`")


def setup(bot: Bot):
    bot.add_cog(Utility(bot))
