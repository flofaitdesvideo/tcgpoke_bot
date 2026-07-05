import discord

from discord import app_commands
from discord.ext import commands

from service.inventory import search_inventory
from views.card_view import (
    CardView,
    build_card_embed,
)


class Card(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="card",
        description="Affiche une carte de ta collection"
    )
    @app_commands.describe(
        nom="Nom de la carte à chercher dans ta collection"
    )
    async def card(
        self,
        interaction: discord.Interaction,
        nom: str
    ):

        await interaction.response.defer()

        results = search_inventory(
            interaction.user.id,
            query=nom,
            sort="value"
        )

        if not results:
            return await interaction.followup.send(
                f"❌ Aucune carte trouvée pour `{nom}` dans ta collection."
            )

        query = nom.lower().strip()

        exact_results = [
            card for card in results
            if card.get("name", "").lower() == query
        ]

        if exact_results:
            selected_card = exact_results[0]
        else:
            selected_card = results[0]

        embed = build_card_embed(
            selected_card,
            interaction.user
        )

        if len(results) > 1:
            other_cards = []

            for card in results[1:6]:
                emoji = card.get("rarity_emoji", "🎴")
                name = card.get("name", "Carte inconnue")
                count = card.get("count", 1)

                other_cards.append(
                    f"{emoji} **{name}** x{count}"
                )

            if other_cards:
                embed.add_field(
                    name=f"🔎 Autres résultats ({len(results) - 1})",
                    value="\n".join(other_cards),
                    inline=False
                )

        view = CardView(
            interaction.user.id,
            selected_card["id"]
        )

        await interaction.followup.send(
            embed=embed,
            view=view
        )


async def setup(bot):
    await bot.add_cog(Card(bot))