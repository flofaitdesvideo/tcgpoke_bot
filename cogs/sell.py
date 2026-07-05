import discord

from discord import app_commands
from discord.ext import commands

from service.database import add_coins
from service.inventory import (
    search_inventory,
    get_card,
    get_card_count,
    get_duplicates,
    remove_card,
)
from service.missions import record_mission_progress

# ============================================================
# CONFIG VENTE
# ============================================================

SELL_MULTIPLIER = 10


# ============================================================
# OUTILS
# ============================================================

def get_card_sell_price(card) -> int:
    value = int(card.get("value", 1))
    return max(5, value * SELL_MULTIPLIER)


def format_card_sell_line(card, amount: int = 1) -> str:
    emoji = card.get("rarity_emoji", "🎴")
    name = card.get("name", "Carte inconnue")
    rarity = card.get("rarity", "Inconnue")
    count = card.get("count", 1)
    price = get_card_sell_price(card) * amount

    return (
        f"{emoji} **{name}** x{amount}\n"
        f"Rareté : `{rarity}`\n"
        f"Copies possédées : `{count}`\n"
        f"Gain : **{price} PokéCoins**"
    )


def build_sell_choices(user_id, current: str):
    current = current or ""

    results = search_inventory(
        user_id,
        query=current,
        sort="value"
    )

    choices = []

    for card in results:
        count = int(card.get("count", 1))

        # On propose seulement les cartes avec doublons
        if count <= 1:
            continue

        card_id = str(card.get("id", ""))
        emoji = card.get("rarity_emoji", "🎴")
        name = card.get("name", "Carte inconnue")
        rarity = card.get("rarity", "Inconnue")
        price = get_card_sell_price(card)

        label = f"{emoji} {name} x{count} • {rarity} • {price} coins"

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
# COG SELL
# ============================================================

class Sell(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def autocomplete_card(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        return build_sell_choices(
            interaction.user.id,
            current
        )

    @app_commands.command(
        name="sell",
        description="Vends une carte en double contre des PokéCoins"
    )
    @app_commands.describe(
        carte="Carte à vendre",
        quantite="Nombre de copies à vendre"
    )
    @app_commands.autocomplete(
        carte=autocomplete_card
    )
    async def sell(
        self,
        interaction: discord.Interaction,
        carte: str,
        quantite: int = 1
    ):

        await interaction.response.defer()

        if quantite <= 0:
            return await interaction.followup.send(
                "❌ La quantité doit être supérieure à 0.",
                ephemeral=True
            )

        user_id = interaction.user.id

        card = get_card(
            user_id,
            carte
        )

        if not card:
            results = search_inventory(
                user_id,
                query=carte,
                sort="value"
            )

            if not results:
                return await interaction.followup.send(
                    "❌ Carte introuvable dans ta collection.",
                    ephemeral=True
                )

            card = results[0]

        card_id = card["id"]
        count = get_card_count(
            user_id,
            card_id
        )

        if count <= 1:
            return await interaction.followup.send(
                "❌ Tu ne peux pas vendre ton dernier exemplaire de cette carte.",
                ephemeral=True
            )

        max_sellable = count - 1

        if quantite > max_sellable:
            quantite = max_sellable

        price_per_card = get_card_sell_price(card)
        total_gain = price_per_card * quantite

        success = remove_card(
            user_id,
            card_id,
            amount=quantite
        )

        if not success:
            return await interaction.followup.send(
                "❌ Impossible de vendre cette carte.",
                ephemeral=True
            )

        add_coins(
            user_id,
            total_gain
        )

        embed = discord.Embed(
            title="💰 Carte vendue !",
            description=format_card_sell_line(
                card,
                amount=quantite
            ),
            color=discord.Color.green()
        )

        embed.set_footer(
            text="Le dernier exemplaire d'une carte est toujours conservé."
        )

        record_mission_progress(
            user_id,
            "card_sold",
            quantite
        )

        await interaction.followup.send(
            embed=embed
        )

    @app_commands.command(
        name="sell_duplicates",
        description="Vends tous tes doublons de cartes Pokémon TCG"
    )
    async def sell_duplicates(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.defer()

        user_id = interaction.user.id
        duplicates = get_duplicates(user_id)

        if not duplicates:
            return await interaction.followup.send(
                "📭 Tu n'as aucun doublon à vendre."
            )

        total_gain = 0
        sold_cards = []
        sold_count = 0

        for card in duplicates:
            count = int(card.get("count", 1))

            if count <= 1:
                continue

            amount_to_sell = count - 1
            card_id = card["id"]

            price = get_card_sell_price(card) * amount_to_sell

            success = remove_card(
                user_id,
                card_id,
                amount=amount_to_sell
            )

            if success:
                total_gain += price
                sold_count += amount_to_sell

                sold_cards.append(
                    f"{card.get('rarity_emoji', '🎴')} **{card.get('name', 'Carte inconnue')}** x{amount_to_sell} → **{price} coins**"
                )

        if total_gain <= 0:
            return await interaction.followup.send(
                "❌ Aucun doublon n'a pu être vendu."
            )

        add_coins(
            user_id,
            total_gain
        )

        text = "\n".join(sold_cards[:15])

        if len(sold_cards) > 15:
            text += f"\n... et **{len(sold_cards) - 15}** autre(s) carte(s)."

        embed = discord.Embed(
            title="💰 Doublons vendus !",
            description=(
                f"Tu as vendu **{sold_count}** carte(s) en double.\n\n"
                f"{text}\n\n"
                f"Gain total : **{total_gain} PokéCoins**"
            ),
            color=discord.Color.gold()
        )

        embed.set_footer(
            text="Le bot garde toujours 1 exemplaire de chaque carte."
        )

        embed.set_footer(
            text="Le bot garde toujours 1 exemplaire de chaque carte."
        )

        record_mission_progress(
            user_id,
            "card_sold",
            sold_count
        )

        await interaction.followup.send(
            embed=embed
        )
        


async def setup(bot):
    await bot.add_cog(Sell(bot))