from discord.ext import commands
from discord import Message, Object
from re import compile
from typing import Union
from time import time
from collections import defaultdict
from json import loads

from source import Bot
from source.utils.defaults import (
    INCREMENT,
    MODIFIERS,
    COOLDOWN,
    ALGORITHM,
    LEVELUP,
    ROLES,
)
from helpers.algorithms import Linear, Quadratic

algos = {
    "linear": Linear,
    "quadratic": Quadratic,
}


class Listener(commands.Cog):
    """Core XP functionality for Maelstrom."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.pattern = None
        self.cooldowns = defaultdict(int)
        self.cache = {}

        self.debugging = True

    def debug(self, *args):
        """Debug print a line, only if debug mode is enabled."""
        if self.debugging:  # TODO: Use logging module debugs
            print(*args)

    def get_modifier(self, message: Message, modifiers: dict) -> Union[float, int]:
        """Gets the overall modifier for XP."""
        modifiers = {int(k): v for k, v in modifiers.items()}
        overall = 1

        usermod = modifiers.get(message.author.id)
        if usermod == 0:
            self.debug("User", message.author.id, "has modifier overriden to 0")
            return 0
        elif usermod:
            overall = usermod

        channelmod = modifiers.get(message.channel.id)
        if channelmod == 0:
            self.debug("Channel", message.channel.id, "has modifier overriden to 0")
            return 0
        elif channelmod:
            overall = channelmod

        if message.channel.category:
            catmod = modifiers.get(message.channel.id)
            if catmod == 0:
                self.debug(
                    "Category", message.category.id, "has modifier overriden to 0"
                )
                return 0
            elif catmod:
                overall = catmod

        role_overall = 0
        for role in message.author.roles:
            rolemod = modifiers.get(role.id)
            if rolemod is None:
                continue
            if rolemod == 0:
                self.debug("Role", role.id, "has modifier overriden to 0")
                return 0
            elif rolemod:
                if rolemod > role_overall:
                    role_overall = rolemod

        return overall

    def cooldown(self, message: Message, cooldown: int) -> bool:
        """Get whether a user is on cooldown."""
        bucket = f"{message.author.id}/{message.guild.id}"
        now = time()

        if self.cooldowns[bucket] > now:
            return True

        self.cooldowns[bucket] = now + cooldown
        return False

    async def calc_xp(self, message: Message, to_add: int):
        """Calculate a user's current and new XP."""
        current_xp = self.cache.get(message.author.id)
        should_create = False
        if current_xp is None:
            user = await self.bot.db.fetch_user(message.author.id, message.guild.id)
            if not user:
                current_xp = 0
                should_create = True
            elif user["banned"]:
                self.debug("User", message.author.id, "is banned, ignoring.")
                return
            else:
                current_xp = user["xp"]
        self.cache[message.author.id] = new = current_xp + to_add

        if should_create:
            await self.bot.db.create_user(message.author.id, message.guild.id, new)
        else:
            await self.bot.db.add_xp(message.author.id, message.guild.id, to_add)

        return current_xp, new

    async def level_up(self, message: Message, config: dict, level: int, required: int):
        """Execute a levelup."""
        try:
            method = config.get("method", "dm")
            if method == "dm":
                await message.author.send(
                    f"🎉 Congrats! You levelled up to level {level} in {message.guild}. You need {required} more xp to get to level {level + 1}! 🎉"
                )
            elif method == "chat":
                await message.channel.send(
                    f"🎉 Congrats {message.author.mention}! You levelled up to level {level}. You need {required} more xp to get to level {level + 1}! 🎉"
                )
            elif method == "react":
                await message.add_reaction("🎉")
        except Exception as e:
            print(e)

    @staticmethod
    def get_roles(config: dict, current: list, level: int) -> dict:
        roles = [(int(k), v) for k, v in config.items()]  # [(level, role)]
        roles.sort(reverse=True)

        for role in roles:
            if role[0] <= level:
                break

        add = None
        remove = []

        if role[1] not in current:
            add = role[1]

        for cr in current:
            if cr != role[1] and cr in config.values():
                remove.append(cr)

        return {
            "add": add,
            "remove": remove,
        }

    async def check_roles(self, message: Message, config: dict, level: int):
        """Apply the correct level roles to a user."""
        if not config:
            return

        results = self.get_roles(config, [r.id for r in message.author.roles], level)

        if add := results["add"]:
            await message.author.add_roles(Object(id=add))

        if remove := results["remove"]:
            for role in remove:
                await message.author.remove_roles(Object(id=role))

    @commands.Cog.listener()
    async def on_ready(self):
        self.pattern = compile(r"^<@!?" + str(self.bot.user.id) + r">$")

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        start = time()
        if not message.guild:
            return

        # Ignore bots
        if message.author.bot:
            return

        # Try to wait until we've filled the cache, might need to remove if in lots of guilds
        await self.bot.wait_until_ready()

        guild_id = message.guild.id
        guild = await self.bot.db.fetch_guild(guild_id)

        # Guild isnt set up, return
        if not guild:
            return

        # Ignore messages starting with the prefix
        if message.content.startswith(guild["prefix"]):
            return

        # Respond with prefix if the bot is mentioned
        try:
            if self.pattern.search(message.content):
                await message.delete()
                return await message.author.send(
                    f"The prefix in **{message.guild}** is: `{guild['prefix']}`"
                )
        except:
            self.debug("Received message but help isnt ready, ignoring error.")

        # Get the guild config
        config = loads(
            guild["config"]
        )  # TODO: Caching so that we don't load the config every time
        default = config.get("default", 30)
        levelinc = config.get("increment", INCREMENT)
        modifiers = config.get("modifiers", MODIFIERS)
        cooldown = config.get("cooldown", COOLDOWN)
        algorithm = algos[config.get("algorithm", ALGORITHM)]
        levelup_config = config.get("levelup", LEVELUP)
        roles = config.get("roles", ROLES)

        # Get the XP modifier, highest role modifier is chosen from roles,
        # highest precendence modifier set overall is chosen,
        # precedence is user, channel, category, roles
        # If ANY modifier is explicitly 0, the overall modifier will be 0
        modifier = self.get_modifier(message, modifiers)
        self.debug("Overall modifier is", modifier)

        if modifier == 0:
            return  # No point doing calcs just to make it 0

        # Check if the user is on cooldown, if yes return
        if self.cooldown(message, cooldown):
            self.debug("User", message.author.id, "is on cooldown")
            return

        to_add = int(default * modifier)
        if not to_add:
            self.debug("Modifier wasn't 0, but mod*def still returned 0, ignoring.")
            return

        current_xp, new = await self.calc_xp(message, to_add)

        level, required, levelup = algorithm.calc(current_xp, new, levelinc)

        try:
            await self.check_roles(message, roles, level)
        except Exception as e:
            print("Roles assignment failed", e)

        self.debug("Operation completed in", time() - start)
        if (not levelup) or not levelup_config:
            return

        await self.level_up(message, levelup_config, level, required)


def setup(bot: Bot):
    bot.add_cog(Listener(bot))
