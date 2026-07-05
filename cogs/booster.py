import discord
from discord import app_commands
from discord.ext import commands

from service.tcg_api import get_valid_sets
from service.booster import open_booster
from service.booster_animation import play_booster_animation
from views.extension_view import ExtensionView

from service.database import update_user_profile
class Booster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="booster")
    async def booster(self, interaction: discord.Interaction):
        await interaction.response.defer()
        sets = await get_valid_sets()
        user = await update_user_profile(interaction.user)
        view = ExtensionView(sets)

        await interaction.followup.send(
            "🎁 Choisis ton extension",
            view=view
        )

    async def open_animation(self, interaction, set_id):

        await interaction.response.defer()

        cards = await open_booster(set_id=set_id)

        if not cards:
            return await interaction.followup.send("❌ Booster vide")

        await play_booster_animation(interaction, cards)


# 👇👇👇 HORS DE LA CLASSE (OBLIGATOIRE)
async def setup(bot):
    await bot.add_cog(Booster(bot))