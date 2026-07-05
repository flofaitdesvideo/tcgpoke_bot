import sys
import os


# ajoute la racine du projet dans Python
ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.insert(
    0,
    ROOT
)


import discord
from discord.ext import commands

import logging


from bot import config
from bot.config import require_env



logging.basicConfig(
    level=logging.INFO
)



intents = discord.Intents.all()


bot = commands.Bot(
    command_prefix=config.PREFIX,
    intents=intents
)



@bot.event
async def on_ready():

    print(
        f"✅ Connecté : {bot.user}"
    )

    await bot.tree.sync()

    print(
        "✅ Slash commands synchronisées"
    )



@bot.event
async def on_error(
    event,
    *args,
    **kwargs
):

    logging.exception(
        event
    )



async def load_cogs():

    for file in os.listdir(
        "cogs"
    ):

        if file.endswith(".py"):

            print(
                f"Chargement : {file}"
            )

            await bot.load_extension(
                f"cogs.{file[:-3]}"
            )



async def start():

    await load_cogs()

    await bot.start(
        require_env("DISCORD_TOKEN", config.DISCORD_TOKEN)
    )



if __name__ == "__main__":

    import asyncio

    asyncio.run(
        start()
    )
    