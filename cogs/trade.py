import discord

from discord import app_commands
from discord.ext import commands

from service.trade import find_trade_card
from service.inventory import search_inventory

from views.trade_view import (
    TradeView,
    build_trade_embed,
)


# ============================================================
# OUTILS AUTOCOMPLETE
# ============================================================

def build_card_choices(user_id, current: str):
    """
    Crée les suggestions Discord pour les cartes.
    Maximum 25 choix.
    """

    current = current or ""

    results = search_inventory(
        user_id,
        query=current,
        sort="value"
    )

    choices = []
    used_ids = set()

    for card in results:

        card_id = str(card.get("id", ""))

        if not card_id or card_id in used_ids:
            continue

        used_ids.add(card_id)

        emoji = card.get("rarity_emoji", "🎴")
        name = card.get("name", "Carte inconnue")
        rarity = card.get("rarity", "Inconnue")
        count = card.get("count", 1)

        label = f"{emoji} {name} x{count} • {rarity}"

        choices.append(
            app_commands.Choice(
                name=label[:100],
                value=card_id[:100]
            )
        )

        if len(choices) >= 25:
            break

    return choices


# ============================================================
# COG TRADE
# ============================================================

class Trade(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def autocomplete_ma_carte(
        self,
        interaction: discord.Interaction,
        current: str
    ):

        return build_card_choices(
            interaction.user.id,
            current
        )

    async def autocomplete_sa_carte(
        self,
        interaction: discord.Interaction,
        current: str
    ):

        joueur = getattr(
            interaction.namespace,
            "joueur",
            None
        )

        if not joueur:
            return []

        return build_card_choices(
            joueur.id,
            current
        )

    @app_commands.command(
        name="trade",
        description="Propose un échange de cartes Pokémon TCG"
    )
    @app_commands.describe(
        joueur="Le joueur avec qui tu veux échanger",
        ma_carte="La carte que tu proposes",
        sa_carte="La carte que tu demandes"
    )
    @app_commands.autocomplete(
        ma_carte=autocomplete_ma_carte,
        sa_carte=autocomplete_sa_carte
    )
    async def trade(
        self,
        interaction: discord.Interaction,
        joueur: discord.Member,
        ma_carte: str,
        sa_carte: str
    ):

        await interaction.response.defer()

        if joueur.bot:
            return await interaction.followup.send(
                "❌ Tu ne peux pas échanger avec un bot."
            )

        if joueur.id == interaction.user.id:
            return await interaction.followup.send(
                "❌ Tu ne peux pas échanger avec toi-même."
            )

        offer_card = find_trade_card(
            interaction.user.id,
            ma_carte
        )

        if not offer_card:
            return await interaction.followup.send(
                "❌ Tu ne possèdes pas cette carte."
            )

        requested_card = find_trade_card(
            joueur.id,
            sa_carte
        )

        if not requested_card:
            return await interaction.followup.send(
                f"❌ {joueur.mention} ne possède pas cette carte."
            )

        view = TradeView(
            offerer_id=interaction.user.id,
            target_id=joueur.id,
            offer_card_id=offer_card["id"],
            requested_card_id=requested_card["id"]
        )

        embed = build_trade_embed(
            offerer=interaction.user,
            target=joueur,
            offer_card=offer_card,
            requested_card=requested_card
        )

        await interaction.followup.send(
            content=f"{joueur.mention}, tu as reçu une proposition d'échange.",
            embed=embed,
            view=view
        )


async def setup(bot):
    await bot.add_cog(Trade(bot))