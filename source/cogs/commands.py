from discord.ext import commands
from discord import Embed, TextChannel, CategoryChannel, Role, Member
from typing import Union

from source import Bot
from source.utils.checks import not_banned
from source.utils.context import Context
from source.utils.defaults import INCREMENT, COOLDOWN, ALGORITHM, LEVELUP
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
        embed.set_author(
            name=f"{ctx.author.name} | {ctx.guild}", icon_url=str(ctx.author.avatar_url)
        )

        await ctx.author.send(embed=embed)

    @commands.group(name="config", aliases=["cfg"])
    @commands.check_any(
        commands.has_guild_permissions(manage_guild=True), commands.is_owner()
    )
    @commands.guild_only()
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.member)
    @not_banned()
    async def config(self, ctx: Context):
        """Modify your Maelstrom config."""
        if not ctx.invoked_subcommand:
            await ctx.send_help("config")

    @config.command(name="reset")
    async def cfg_reset(self, ctx: Context):
        """Reset your Maelstrom config."""
        msg = await ctx.send(f"Are you sure you wish to reset your Maelstrom config? [Yes/No]")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            message = await self.bot.wait_for("message", check=check, timeout=30)
        except:
            return await msg.edit(content="Cancelled.")

        if message.content.lower() not in ["yes", "y"]:
            return await msg.edit(content="Cancelled.")

        await self.bot.db.update_guild_config(ctx.guild.id, {})
        await ctx.send("Your Maelstrom config has been successfully reset!")

    @config.group(name="increment", aliases=["inc"])
    async def cfg_inc(self, ctx: Context):
        """Change the level increment config."""
        if not ctx.invoked_subcommand:
            await ctx.send_help("config increment")

    @cfg_inc.command(name="get")
    async def cfg_inc_get(self, ctx: Context):
        """Get the current level increment."""
        config = await ctx.guild_config()
        await ctx.send(
            f"Your current level increment is: {config.get('increment', INCREMENT)} xp"
        )

    @cfg_inc.command(name="set")
    async def cfg_inc_set(self, ctx: Context, *, new: int):
        """Set a new level increment."""
        config = await ctx.guild_config()
        config["increment"] = new
        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(f"Successfully set your level increment to: {new} xp")

    @cfg_inc.command(name="reset")
    async def cfg_inc_reset(self, ctx: Context):
        """Reset the level increment."""
        config = await ctx.guild_config()
        config["increment"] = INCREMENT
        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(f"Successfully reset your level increment to: {INCREMENT} xp")

    @config.group(name="modifiers", aliases=["mod", "mods", "modifier"])
    async def cfg_mod(self, ctx: Context):
        """Change the current modifier config."""
        if not ctx.invoked_subcommand:
            await ctx.send_help("config modifiers")

    @cfg_mod.command(name="get")
    async def cfg_mod_get(self, ctx: Context):
        """Get the current modifier config."""
        config = await ctx.guild_config()
        mods = config.get("modifiers", {})

        if not mods:
            return await ctx.send(f"You don't have any modifiers overriden. To set one up use `{ctx.prefix}config modifiers add <modifier> <value>`")

        roles, users, channels, categories = "", "", "", ""
        for mod, value in mods.items():
            mod = int(mod)
            if ctx.guild.get_role(mod):
                roles += f"<@&{mod}> = {value}\n"
            elif ctx.guild.get_member(mod):
                users += f"<@!{mod}> = {value}\n"
            elif channel := ctx.guild.get_channel(mod):
                if isinstance(channel, TextChannel):
                    channels += f"<#{mod}> = {value}\n"
                elif isinstance(channel, CategoryChannel):
                    categories += f"{channel} = {value}\n"

        embed = Embed(title="Modifier Overrides", colour=0x87CEEB)
        if users: embed.add_field(name="Users", value=users)
        if channels: embed.add_field(name="Channels", value=channels)
        if roles: embed.add_field(name="Roles", value=roles)
        if categories: embed.add_field(name="Categories", value=categories)

        await ctx.send(embed=embed)

    @cfg_mod.command(name="add", aliases=["set"])
    async def cfg_mod_add(self, ctx: Context, target: Union[Member, TextChannel, CategoryChannel, Role], override: float):
        """Add a new modifier override."""
        if not (0 <= override <= 5):
            return await ctx.send("Overrides must be a number between 0 and 5 inclusive. It can have decimals.")
        config = await ctx.guild_config()
        mods = config.get("modifiers", {})

        mods[target.id] = override
        config["modifiers"] = mods

        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(f"Successfully added `{target.id}` as a {type(target).__name__.lower()} override with value: {override}")

    @cfg_mod.command(name="remove", aliases=["del"])
    async def cfg_mod_del(self, ctx: Context, target: Union[Member, TextChannel, CategoryChannel, Role]):
        """Remove an existing modifier override."""
        config = await ctx.guild_config()
        mods = config.get("modifiers", {})

        if str(target.id) not in mods:
            return await ctx.send("There is no modifier for that target.")

        del mods[str(target.id)]
        config["modifiers"] = mods

        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(f"Successfully removed `{target.id}` as a {type(target).__name__.lower()} override")

    @config.group(name="cooldown", aliases=["cd"])
    async def cfg_cd(self, ctx: Context):
        """Change the current cooldown config."""
        if not ctx.invoked_subcommand:
            await ctx.send_help("config cooldown")

    @cfg_cd.command(name="get")
    async def cfg_cd_get(self, ctx: Context):
        """Get the cooldown."""
        config = await ctx.guild_config()
        await ctx.send(
            f"Your current cooldown is: {config.get('cooldown', COOLDOWN)}s"
        )

    @cfg_cd.command(name="set")
    async def cfg_cd_set(self, ctx: Context, *, new: int):
        """Set a new cooldown."""
        config = await ctx.guild_config()
        config["cooldown"] = new
        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(f"Successfully set your cooldown to: {new}s")

    @cfg_cd.command(name="reset")
    async def cfg_cd_reset(self, ctx: Context):
        """Reset the cooldown."""
        config = await ctx.guild_config()
        config["cooldown"] = COOLDOWN
        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(f"Successfully reset your cooldown to: {COOLDOWN}s")

    @config.group(name="algorithm", aliases=["algo"])
    async def cfg_algo(self, ctx: Context):
        """Change the current algorithm config."""
        if not ctx.invoked_subcommand:
            await ctx.send_help("config algorithm")

    @cfg_algo.command(name="get")
    async def cfg_algo_get(self, ctx: Context):
        """Get the algorithm."""
        config = await ctx.guild_config()
        await ctx.send(
            f"Your current algorithm is: {config.get('algorithm', ALGORITHM)}"
        )

    @cfg_algo.command(name="set")
    async def cfg_algo_set(self, ctx: Context, *, new: str):
        """Set a new algorithm."""
        new = new.lower()
        if not new in algos:
            return await ctx.send(f"Valid algorithms: {', '.join([k for k in algos.keys()])}")
        config = await ctx.guild_config()
        config["algorithm"] = new
        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(f"Successfully set your algorithm to: {new}")

    @cfg_algo.command(name="reset")
    async def cfg_algo_reset(self, ctx: Context):
        """Reset the algorithm."""
        config = await ctx.guild_config()
        config["algorithm"] = ALGORITHM
        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(f"Successfully reset your algorithm to: {ALGORITHM}")

    @config.group(name="levelup", aliases=["lu"])
    async def cfg_lu(self, ctx: Context):
        """Change the current levelup action config."""
        if not ctx.invoked_subcommand:
            await ctx.send_help("config levelup")

    @cfg_lu.command(name="get")
    async def cfg_lu_get(self, ctx: Context):
        """Get the levelup action."""
        config = await ctx.guild_config()
        await ctx.send(
            f"Your current levelup action is: {config.get('levelup', LEVELUP)['method']}"
        )

    @cfg_lu.command(name="set")
    async def cfg_lu_set(self, ctx: Context, *, new: str):
        """Set a new levelup action."""
        new = new.lower()
        lus = ["dm", "chat", "react"]
        if not new in lus:
            return await ctx.send(f"Valid levelup actions: {', '.join(lus)}")
        config = await ctx.guild_config()
        config["levelup"] = {"method":new}
        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(f"Successfully set your levelup action to: {new}")

    @cfg_lu.command(name="reset")
    async def cfg_lu_reset(self, ctx: Context):
        """Reset the levelup action."""
        config = await ctx.guild_config()
        config["levelup"] = LEVELUP
        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(f"Successfully reset your levelup action to: {LEVELUP['method']}")


def setup(bot: Bot):
    bot.add_cog(Commands(bot))
