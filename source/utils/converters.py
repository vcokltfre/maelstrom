from discord.ext import commands
from typing import Union
from types import ModuleType

from .context import Context


class SourceConverter(commands.Converter):
    """A Converter that converts a string to a Command, Cog or Extension."""

    async def convert(
        self, ctx: Context, argument: str
    ) -> Union[commands.Command, commands.Cog, ModuleType]:
        if command := ctx.bot.get_command(argument):
            if command.name == "help":
                return ctx.bot.help_command
            return command

        if cog := ctx.bot.get_cog(argument):
            return cog

        if extension := ctx.bot.extensions.get(argument):
            return extension
        raise commands.BadArgument("Not a valid Command, Cog nor Extension.")
