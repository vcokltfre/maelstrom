from discord.ext import commands
from discord import Embed
from typing import Optional
from asyncio import sleep

from source import Bot
from source.utils.checks import not_banned


class Utility(commands.Cog):
    """A set of utility commands for Maelstrom."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="prefix")
    @commands.check_any(
        commands.has_guild_permissions(manage_guild=True), commands.is_owner()
    )
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

    @commands.command(name="invite")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.member)
    async def invite(self, ctx: commands.Context):
        try:
            await ctx.message.delete()
        except:
            print("Couldn't delete message")
        embed = Embed(title="Invite Maelstrom", colour=0x87CEEB)
        embed.description = "[Invite Me!](https://l.vcokltf.re/maelstrom)\n"
        embed.description += "[Join my Support Server!](https://discord.gg/SWZ2bybPcg)"
        await ctx.author.send(embed=embed)

    @commands.command(name="mee6import")
    @commands.is_owner()
    async def mee6import(self, ctx: commands.Context, guild: int):
        """Import a guild using MEE6 into Maelstrom."""
        await ctx.send(f"Import guild {guild} from MEE6?")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            resp = await self.bot.wait_for("message", check=check, timeout=30)
        except:
            return

        if resp.content.lower() not in ["yes", "y"]:
            return

        await ctx.send("Starting import...")
        await self.bot.db.clear_guild(guild)

        pages = 0
        user_count = 0
        userdata = {}

        while True:
            page = await self.bot.session.get(
                f"https://mee6.xyz/api/plugins/levels/leaderboard/{guild}?page={pages}"
            )
            if page.status >= 400:  # TODO: figure out how to deal with the ratelimits
                print(page.status, page.headers)
                break

            pages += 1

            data = await page.json()
            users = data["players"]

            for user in users:
                user_count += 1
                userdata[user["id"]] = (int(user["id"]), guild, user["xp"], 0, False)

            print(f"Page {pages} | Sleeping")
            await sleep(1)

        await ctx.send(
            f"Successfully downloaded {pages + 1} pages ({user_count + 1} users) from MEE6 levelling, transferring to db..."
        )

        await self.bot.db.add_users([v for v in userdata.values()])

        await ctx.send("Finished!")


def setup(bot: Bot):
    bot.add_cog(Utility(bot))
