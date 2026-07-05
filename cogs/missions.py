import discord

from discord import app_commands
from discord.ext import commands

from service.missions import get_all_mission_statuses
from views.missions_view import (
    MissionsView,
    build_missions_embed,
)


class Missions(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="missions",
        description="Affiche tes missions quotidiennes Pokémon TCG"
    )
    async def missions(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.defer()

        statuses = get_all_mission_statuses(
            interaction.user.id
        )

        view = MissionsView(
            interaction.user.id
        )

        await interaction.followup.send(
            embed=build_missions_embed(
                interaction.user,
                statuses
            ),
            view=view
        )


async def setup(bot):
    await bot.add_cog(Missions(bot))