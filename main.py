from dotenv import load_dotenv
from os import getenv

from source import Bot

load_dotenv()

if __name__ == "__main__":
    bot = Bot()

    bot.load_cogs(
        "jishaku",
        "source.cogs.utility",
    )

    bot.run(getenv("TOKEN"))
