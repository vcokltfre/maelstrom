from discord.ext.commands import check, Context


def not_banned():
    async def predicate(ctx: Context):
        user = await ctx.bot.db.user_is_banned(ctx.author.id)
        if user and user["banned"]:
            return False

        if ctx.guild:
            guild = await ctx.bot.db.fetch_guild(ctx.guild.id)
            if guild and guild["banned"]:
                return False

        return True

    return check(predicate)


def in_guild_or_dm(guild_id: int):
    async def predicate(ctx: Context):
        if not ctx.guild:
            return True
        return ctx.guild.id == guild_id

    return check(predicate)
