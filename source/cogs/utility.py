from discord.ext import commands
from discord import Embed
from typing import Optional, Union, Tuple
from types import ModuleType
from asyncio import sleep
from pathlib import Path
from inspect import getsourcefile, getsourcelines

from source import Bot
from source.utils.checks import not_banned, in_guild_or_dm
from source.utils.context import Context
from source.utils.converters import SourceConverter


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
    async def prefix(self, ctx: Context, *, new: Optional[str]):
        wording = "updated" if new else "reset"
        prefix = new or "!"

        if len(prefix) > 64:
            return await ctx.send("Your prefix can't be longer than 64 characters.")

        await self.bot.db.update_guild_prefix(ctx.guild.id, prefix)

        await ctx.send(f"Your prefix for this server has been {wording} to: `{prefix}`")

    @commands.command(name="invite")
    @commands.cooldown(rate=1, per=3, type=commands.BucketType.member)
    async def invite(self, ctx: Context):
        try:
            await ctx.message.delete()
        except:
            print("Couldn't delete message")
        embed = Embed(title="Invite Maelstrom", colour=0x87CEEB)
        embed.description = "[Invite Me!](https://l.vcokltf.re/maelstrom)\n"
        embed.description += "[Join my Support Server!](https://discord.gg/SWZ2bybPcg)"
        embed.set_author(name="Maelstrom", icon_url=str(self.bot.user.avatar_url))
        await ctx.author.send(embed=embed)

    @commands.command(name="mee6import")
    @commands.is_owner()
    async def mee6import(self, ctx: Context, guild: int):
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

    @commands.command(aliases=("src", "github", "git"), invoke_without_command=True)
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.member)
    @in_guild_or_dm(683009037830324235)#(815301491916144650)
    async def source(self, ctx: Context, *, source_item: SourceConverter = None):
        """Shows the github repo for this bot, include a command, cog, or extension to got to that file."""
        if source_item is None:
            embed = Embed(
                title="Magoji's Github Repository",
                description=f"[Here's the github link!](https://github.com/vcokltfre/maelstrom)",
                colour=0x87CEEB,
            )
            return await ctx.send(embed=embed)
        embed = self.build_embed(source_item)
        await ctx.send(embed=embed)

    def build_embed(self, source_object):
        """Build embed based on source object."""
        url, location, first_line = self.get_github_url(source_object)

        if isinstance(source_object, commands.HelpCommand):
            title = "Help Command"
            help_cmd = self.bot.get_command("help")
            description = help_cmd.help
        elif isinstance(source_object, commands.Command):
            description = source_object.short_doc
            title = f"Command: {source_object.qualified_name}"
        elif isinstance(source_object, ModuleType):
            title = f"Extension: {source_object.__name__}"
        else:
            title = f"Cog: {source_object.qualified_name}"
            description = source_object.description.splitlines()[0]

        embed = Embed(title=title, description=description, colour=0x87CEEB)
        embed.add_field(name="Source Code", value=f"[Here's the Github link!]({url})")
        line_text = f":{first_line}" if first_line else ""
        embed.set_footer(text=f"{location}{line_text}")

        return embed

    def get_github_url(self, source_item):
        if isinstance(source_item, (commands.HelpCommand, commands.Cog)):
            src = type(source_item)
            filename = getsourcefile(src)
        elif isinstance(source_item, commands.Command):
            src = source_item.callback.__code__
            filename = src.co_filename
        elif isinstance(source_item, ModuleType):
            src = source_item
            filename = src.__file__

        lines, first_line_no = self.get_source_code(source_item)
        if first_line_no:
            lines_extension = f"#L{first_line_no}-L{first_line_no+len(lines)-1}"
        lines_extension = lines_extension or ""

        file_location = Path(filename).relative_to(Path.cwd()).as_posix()

        url = f"https://github.com/vcokltfre/maelstrom/blob/master/{file_location}{lines_extension}"

        return url, file_location, first_line_no or None

    def get_source_code(
        self, source_item: Union[commands.Command, commands.Cog, ModuleType]
    ) -> Tuple[str, int]:
        if isinstance(source_item, ModuleType):
            source = getsourcelines(source_item)
        elif isinstance(source_item, (commands.Cog, commands.HelpCommand)):
            source = getsourcelines(type(source_item))
        elif isinstance(source_item, commands.Command):
            source = getsourcelines(source_item.callback)

        return source


def setup(bot: Bot):
    bot.add_cog(Utility(bot))
