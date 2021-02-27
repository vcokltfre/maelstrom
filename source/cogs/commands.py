from discord.ext import commands
from discord import Embed

from source import Bot
from source.utils.checks import not_banned
from source.utils.context import Context
from helpers.algorithms import Linear, LinearIncremental, Quadratic

algos = {
    "linear": Linear,
    "linearinc": LinearIncremental,
    "quadratic": Quadratic,
}


class Commands(commands.Cog):
    """A set of user commands for Maelstrom."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    @commands.guild_only()
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.member)
    @not_banned()
    async def leaderboard(self, ctx: Context):
        async with ctx.typing():
            top = await self.bot.db.fetch_top_users(ctx.guild.id)
            guild = await ctx.guild_config()
            algorithm = algos[guild.get("algorithm", "linear")]
            inc = guild.get("increment", 300)

            embed = Embed(title=f"Top Users in {ctx.guild}", colour=0x87CEEB)

            for i, user in enumerate(top):
                id = user["id"]
                xp = user["xp"]
                member = ctx.guild.get_member(id)

                if not member:
                    member = "User Not Found"

                level, required = algorithm.get_level(xp, inc)

                embed.add_field(
                    name=f"{i + 1} | {member}",
                    value=f"XP: {xp}\nLevel: {level}\nLevel-up: {required} xp",
                    inline=True,
                )

            await ctx.send(embed=embed)

    @commands.command(name="rank", aliases=["level"])
    @commands.guild_only()
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.member)
    @not_banned()
    async def rank(self, ctx: Context):
        user = await self.bot.db.fetch_user(ctx.author.id, ctx.guild.id)

        try:
            await ctx.message.delete()
        except:
            pass

        if not user:
            await ctx.author.send(
                "There isn't any rank info on you yet, try talking some more!"
            )

        guild = await ctx.guild_config()
        algorithm = algos[guild.get("algorithm", "linear")]
        inc = guild.get("increment", 300)
        xp = user["xp"]

        level, required = algorithm.get_level(xp, inc)

        rank = await self.bot.db.get_rank(ctx.author.id, ctx.guild.id)

        embed = Embed(
            description=f"Server Ranking: #{rank['rank']}\nServer Level: {level}\nServer XP: {xp} xp\nLevel-up: {required} xp",
            colour=0x87CEEB,
        )
        embed.set_author(name=f"{ctx.author.name} | {ctx.guild}", icon_url=str(ctx.author.avatar_url))

        await ctx.author.send(embed=embed)


def setup(bot: Bot):
    bot.add_cog(Commands(bot))
