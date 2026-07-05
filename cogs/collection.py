import discord

from typing import Optional

from discord import app_commands
from discord.ext import commands

from views.collection_view import CollectionView
from service.inventory import get_inventory_stats

from service.database import update_user_profile
class Collection(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="collection",
        description="Affiche ta collection de cartes Pokémon TCG"
    )
    @app_commands.describe(
        recherche="Nom d'une carte à chercher",
        rarete="Filtrer par rareté",
        tri="Trier les cartes",
        favoris="Afficher uniquement tes cartes favorites"
    )
    @app_commands.choices(
        rarete=[
            app_commands.Choice(name="Commune", value="common"),
            app_commands.Choice(name="Peu commune", value="uncommon"),
            app_commands.Choice(name="Rare", value="rare"),
            app_commands.Choice(name="Holo", value="holo"),
            app_commands.Choice(name="Ultra rare", value="ultra"),
            app_commands.Choice(name="Secrète", value="secret"),
        ],
        tri=[
            app_commands.Choice(name="Nom", value="name"),
            app_commands.Choice(name="Rareté", value="rarity"),
            app_commands.Choice(name="Valeur", value="value"),
            app_commands.Choice(name="Nombre de copies", value="count"),
            app_commands.Choice(name="Extension", value="set"),
        ]
    )
    async def collection(
        self,
        interaction: discord.Interaction,
        recherche: Optional[str] = "",
        rarete: Optional[str] = None,
        tri: Optional[str] = "name",
        favoris: Optional[bool] = False
    ):

        await interaction.response.defer()

        user = await update_user_profile(interaction.user)
        stats = get_inventory_stats(interaction.user.id)

        if stats["total_cards"] <= 0:
            return await interaction.followup.send(
                "📭 Tu n'as aucune carte pour le moment. Ouvre un booster avec `/booster`."
            )

        view = CollectionView(
            user_id=interaction.user.id,
            query=recherche or "",
            rarity=rarete,
            favorites_only=favoris or False,
            sort=tri or "name",
            page=0
        )

        await interaction.followup.send(
            embed=view.build_embed(interaction),
            view=view
        )


async def setup(bot):
    await bot.add_cog(Collection(bot))