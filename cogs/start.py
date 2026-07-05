import discord
from discord import app_commands
from discord.ext import commands

from bot.database import get_user



class Start(commands.Cog):

    def __init__(self, bot):
        self.bot = bot



    @app_commands.command(
        name="start",
        description="Créer ton compte TCG"
    )
    async def start(
        self,
        interaction: discord.Interaction
    ):


        user = get_user(
            interaction.user.id
        )


        await interaction.response.send_message(
            "🎉 Ton compte Pokémon TCG est prêt !\n"
            "Tu reçois 100 🪙 coins."
        )



async def setup(bot):

    await bot.add_cog(
        Start(bot)
    )