from discord.ext.commands import check, Context

def not_banned():
    async def predicate(ctx: Context):
        user = await ctx.bot.db.fetch_user(ctx.author.id)
        if user and user["banned"]:
            return False

        if ctx.guild:
            guild = await ctx.bot.db.fetch_guild(ctx.guild.id)
            if guild and guild["banned"]:
                return False

        return True

    return check(predicate)
