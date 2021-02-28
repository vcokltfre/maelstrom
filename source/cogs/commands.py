from discord.ext import commands
from discord import Embed, TextChannel, CategoryChannel, Role, Member
from typing import Union

from source import Bot
from source.utils.checks import not_banned
from source.utils.context import Context
from source.utils.defaults import DM_RANK, INCREMENT, COOLDOWN, ALGORITHM, LEVELUP, ROLES
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
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.member)
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
        dm_rank = guild.get("dm_rank", True)

        level, required = algorithm.get_level(xp, inc)

        rank = await self.bot.db.get_rank(ctx.author.id, ctx.guild.id)

        embed = Embed(
            description=f"Server Ranking: #{rank['rank']}\nServer Level: {level}\nServer XP: {xp} xp\nLevel-up: {required} xp",
            colour=0x87CEEB,
        )
        embed.set_author(
            name=f"{ctx.author.name} | {ctx.guild}", icon_url=str(ctx.author.avatar_url)
        )

        if dm_rank:
            await ctx.author.send(embed=embed)
        else:
            await ctx.send(embed=embed)
        

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
    
    @config.group(name="dm_rank", aliases = ['rank', 'dm'])
    async def dm_rank(self, ctx: Context):
        """Change the config for the dm_rank option"""
        if not ctx.invoked_subcommand:
            await ctx.send_help("config dm_rank")

    @dm_rank.command(name="get")
    async def dm_rank_get(self, ctx: Context):
        """Get the current value for the dm_rank option"""
        config = await ctx.guild_config()
        val = config.get("dm_rank", DM_RANK)
        if val:
            await ctx.send("Current config: Using the !rank command will dm the output to the user!")
        else:
            await ctx.send("Current config: Using the !rank command will output in the current text channel!")
    
    @dm_rank.command(name="set")
    async def dm_rank_set(self, ctx: Context, value: str):
        """Set if you want !rank to dm the user or display in the guild chat"""
        if not value.lower() in ['true', 'false']:
            return await ctx.send("Invalid Option! Valid Options: true, false")
        opt = value.lower()
        config = await ctx.guild_config()
        if opt == 'true':
            config["dm_rank"] = True
        else:
            config["dm_rank"] = False
        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(f"Successfully updated your config! (dm_rank was set to {value})")
                
    @config.command(name="reset")
    async def cfg_reset(self, ctx: Context):
        """Reset your Maelstrom config."""
        msg = await ctx.send(
            f"Are you sure you wish to reset your Maelstrom config? [Yes/No]"
        )

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
        if not (300 <= new <= 10000):
            return await ctx.send(
                "Increments must be between 300 and 10,0000 inclusive."
            )
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
            return await ctx.send(
                f"You don't have any modifiers overriden. To set one up use `{ctx.prefix}config modifiers add <modifier> <value>`"
            )

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
        if users:
            embed.add_field(name="Users", value=users)
        if channels:
            embed.add_field(name="Channels", value=channels)
        if roles:
            embed.add_field(name="Roles", value=roles)
        if categories:
            embed.add_field(name="Categories", value=categories)

        await ctx.send(embed=embed)

    @cfg_mod.command(name="add", aliases=["set"])
    async def cfg_mod_add(
        self,
        ctx: Context,
        target: Union[Member, TextChannel, CategoryChannel, Role],
        override: float,
    ):
        """Add a new modifier override."""
        if not (0 <= override <= 5):
            return await ctx.send(
                "Overrides must be a number between 0 and 5 inclusive. It can have decimals."
            )
        config = await ctx.guild_config()
        mods = config.get("modifiers", {})

        mods[target.id] = override
        config["modifiers"] = mods

        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(
            f"Successfully added `{target.id}` as a {type(target).__name__.lower()} override with value: {override}"
        )

    @cfg_mod.command(name="remove", aliases=["del"])
    async def cfg_mod_del(
        self, ctx: Context, target: Union[Member, TextChannel, CategoryChannel, Role]
    ):
        """Remove an existing modifier override."""
        config = await ctx.guild_config()
        mods = config.get("modifiers", {})

        if str(target.id) not in mods:
            return await ctx.send("There is no modifier for that target.")

        del mods[str(target.id)]
        config["modifiers"] = mods

        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(
            f"Successfully removed `{target.id}` as a {type(target).__name__.lower()} override"
        )

    @config.group(name="cooldown", aliases=["cd"])
    async def cfg_cd(self, ctx: Context):
        """Change the current cooldown config."""
        if not ctx.invoked_subcommand:
            await ctx.send_help("config cooldown")

    @cfg_cd.command(name="get")
    async def cfg_cd_get(self, ctx: Context):
        """Get the cooldown."""
        config = await ctx.guild_config()
        await ctx.send(f"Your current cooldown is: {config.get('cooldown', COOLDOWN)}s")

    @cfg_cd.command(name="set")
    async def cfg_cd_set(self, ctx: Context, *, new: int):
        """Set a new cooldown."""
        if not (10 <= new <= 3600):
            return await ctx.send(
                "Increments must be between 10s and 3,600s inclusive."
            )
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
            return await ctx.send(
                f"Valid algorithms: {', '.join([k for k in algos.keys()])}"
            )
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
        config["levelup"] = {"method": new}
        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(f"Successfully set your levelup action to: {new}")

    @cfg_lu.command(name="reset")
    async def cfg_lu_reset(self, ctx: Context):
        """Reset the levelup action."""
        config = await ctx.guild_config()
        config["levelup"] = LEVELUP
        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(
            f"Successfully reset your levelup action to: {LEVELUP['method']}"
        )

    @config.group(name="roles")
    async def cfg_lr(self, ctx: Context):
        """Change the current level roles config."""
        if not ctx.invoked_subcommand:
            await ctx.send_help("config roles")

    @cfg_lr.command(name="get")
    async def cfg_lr_get(self, ctx: Context):
        """Get the current level roles config."""
        config = await ctx.guild_config()
        config = config.get("roles", ROLES)

        if not config:
            return await ctx.send(
                f"No level roles have been set up yet, create one using `{ctx.prefix}config roles add <level> <role>`"
            )

        desc = ""
        for level, role in config.items():
            role = ctx.guild.get_role(role)
            if not role:
                continue
            desc += f"\n{level}: {role.mention}"

        embed = Embed(title="Level Roles", colour=0x87CEEB, description=desc)
        await ctx.send(embed=embed)

    @cfg_lr.command(name="add", aliases=["set"])
    async def cfg_lr_add(self, ctx: Context, level: int, role: Role):
        """Add a new level role."""
        if not (1 <= level <= 10000):
            return await ctx.send("Levels must be between 1 and 10,0000 inclusive.")

        config = await ctx.guild_config()
        roles = config.get("roles", ROLES)

        if len(roles) >= 25:
            return await ctx.send(
                "For performance reasons, you can't have more than 25 level roles, please remove a level role before adding a new one."
            )

        roles[str(level)] = role.id
        config["roles"] = roles

        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(
            f"Successfully added `{role.id}` as the level role for level {level}"
        )

    @cfg_lr.command(name="remove", aliases=["del"])
    async def cfg_lr_remove(self, ctx: Context, lr: Union[Role, int]):
        """Remove a level role."""
        config = await ctx.guild_config()
        roles = config.get("roles", ROLES)

        if isinstance(lr, int):
            lr = level = str(lr)
            print(lr, roles)
            if lr not in roles:
                return await ctx.send("That is not a valid level nor role.")
            role = ctx.guild.get_role(roles[lr])
            del roles[lr]
        else:
            level = None
            for k, v in roles.items():
                if v == lr.id:
                    level = k
            if not level:
                return await ctx.send("That is not a valid level nor role.")
            del roles[level]

        config["roles"] = roles

        await self.bot.db.update_guild_config(ctx.guild.id, config)
        await ctx.send(
            f"Successfully removed `{role.id if isinstance(role, Role) else None}` as the level role for level {level}"
        )


def setup(bot: Bot):
    bot.add_cog(Commands(bot))
