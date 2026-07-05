import discord

from discord import app_commands
from discord.ext import commands

from service.database import get_user
from service.inventory import (
    get_inventory_stats,
    get_best_cards,
)
from service.achievements import (
    ACHIEVEMENTS,
    get_unlocked_achievements,
)
from service.database import get_user, update_user_profile
# ============================================================
# OUTILS PROFILE
# ============================================================

def get_xp_needed(level: int) -> int:
    return level * 100


def create_progress_bar(current: int, maximum: int, size: int = 10) -> str:
    if maximum <= 0:
        maximum = 1

    ratio = min(current / maximum, 1)
    filled = int(ratio * size)
    empty = size - filled

    return "█" * filled + "░" * empty


def format_best_card(card):

    if not card:
        return "Aucune carte"

    emoji = card.get("rarity_emoji", "🎴")
    name = card.get("name", "Carte inconnue")
    rarity = card.get("rarity", "Inconnue")
    count = card.get("count", 1)
    set_name = card.get("set", {}).get("name", "Extension inconnue")

    return (
        f"{emoji} **{name}**\n"
        f"Rareté : `{rarity}`\n"
        f"Extension : `{set_name}`\n"
        f"Copies : `{count}`"
    )


# ============================================================
# COG PROFILE
# ============================================================

class Profile(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="profile",
        description="Affiche ton profil Pokémon TCG"
    )
    async def profile(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.defer()

        user_id = interaction.user.id

        update_user_profile(interaction.user)
        user_data = get_user(user_id)
        inventory_stats = get_inventory_stats(user_id)
        best_cards = get_best_cards(user_id, limit=1)

        best_card = best_cards[0] if best_cards else None

        coins = user_data.get("coins", 0)
        gems = user_data.get("gems", 0)

        level = user_data.get("level", 1)
        xp = user_data.get("xp", 0)
        xp_needed = get_xp_needed(level)

        stats = user_data.get("stats", {})
        unlocked_achievements = get_unlocked_achievements(
    user_id
)

        achievements_count = len(unlocked_achievements)
        achievements_total = len(ACHIEVEMENTS)
        boosters_opened = stats.get("opened", 0)
        trades = stats.get("trades", 0)
        coins_earned = stats.get("coins_earned", 0)

        progress_bar = create_progress_bar(
            xp,
            xp_needed
        )

        embed = discord.Embed(
            title=f"👤 Profil de {interaction.user.display_name}",
            description=(
                f"⭐ Niveau **{level}**\n"
                f"⚡ XP : **{xp}/{xp_needed}**\n"
                f"`{progress_bar}`"
            ),
            color=discord.Color.purple()
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.add_field(
            name="💰 Économie",
            value=(
                f"🪙 PokéCoins : **{coins}**\n"
                f"💎 Gems : **{gems}**\n"
                f"📈 Coins gagnés : **{coins_earned}**"
            ),
            inline=True
        )

        embed.add_field(
            name="📚 Collection",
            value=(
                f"🃏 Cartes totales : **{inventory_stats['total_cards']}**\n"
                f"🎴 Cartes uniques : **{inventory_stats['unique_cards']}**\n"
                f"🔁 Doublons : **{inventory_stats['duplicates']}**\n"
                f"⭐ Favoris : **{inventory_stats['favorites']}**\n"
                f"💎 Valeur : **{inventory_stats['value']}**"
            ),
            inline=True
        )

        embed.add_field(
            name="🎁 Activité",
            value=(
                f"Boosters ouverts : **{boosters_opened}**\n"
                f"Échanges réalisés : **{trades}**"
            ),
            inline=False
        )

        embed.add_field(
            name="🌟 Meilleure carte",
            value=format_best_card(best_card),
            inline=False
        )

        if best_card and best_card.get("image"):
            embed.set_image(
                url=best_card.get("image")
            )

        embed.set_footer(
            text="Utilise /booster pour obtenir plus de cartes."
        )

        await interaction.followup.send(
            embed=embed
        )


async def setup(bot):
    await bot.add_cog(Profile(bot))