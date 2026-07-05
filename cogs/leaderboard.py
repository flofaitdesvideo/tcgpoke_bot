import discord

from discord import app_commands
from discord.ext import commands

from service.database import get_all_users


# ============================================================
# OUTILS LEADERBOARD
# ============================================================

def get_inventory_total_cards(user_data):
    inventory = user_data.get("inventory", [])

    total = 0

    for card in inventory:
        total += int(card.get("count", 1))

    return total


def get_inventory_unique_cards(user_data):
    inventory = user_data.get("inventory", [])
    return len(inventory)


def get_inventory_value(user_data):
    inventory = user_data.get("inventory", [])

    total = 0

    for card in inventory:
        value = int(card.get("value", 1))
        count = int(card.get("count", 1))

        total += value * count

    return total


def get_user_score(user_data, mode: str):
    if mode == "coins":
        return int(user_data.get("coins", 0))

    if mode == "level":
        level = int(user_data.get("level", 1))
        xp = int(user_data.get("xp", 0))

        return level * 100000 + xp

    if mode == "cards":
        return get_inventory_total_cards(user_data)

    if mode == "unique":
        return get_inventory_unique_cards(user_data)

    if mode == "value":
        return get_inventory_value(user_data)

    if mode == "boosters":
        stats = user_data.get("stats", {})
        return int(stats.get("opened", 0))

    return 0


def format_score(user_data, mode: str):
    if mode == "coins":
        return f"{int(user_data.get('coins', 0))} PokéCoins"

    if mode == "level":
        return (
            f"Niveau {int(user_data.get('level', 1))} "
            f"· {int(user_data.get('xp', 0))} XP"
        )

    if mode == "cards":
        return f"{get_inventory_total_cards(user_data)} cartes"

    if mode == "unique":
        return f"{get_inventory_unique_cards(user_data)} cartes uniques"

    if mode == "value":
        return f"{get_inventory_value(user_data)} valeur"

    if mode == "boosters":
        stats = user_data.get("stats", {})
        return f"{int(stats.get('opened', 0))} boosters"

    return "0"


def get_leaderboard_title(mode: str):
    titles = {
        "coins": "💰 Classement PokéCoins",
        "level": "⭐ Classement Niveau",
        "cards": "🃏 Classement Cartes Totales",
        "unique": "🎴 Classement Cartes Uniques",
        "value": "💎 Classement Valeur de Collection",
        "boosters": "🎁 Classement Boosters Ouverts",
    }

    return titles.get(mode, "🏆 Leaderboard")


def get_rank_emoji(rank: int):
    if rank == 1:
        return "🥇"

    if rank == 2:
        return "🥈"

    if rank == 3:
        return "🥉"

    return f"`#{rank}`"


# ============================================================
# COG LEADERBOARD
# ============================================================

class Leaderboard(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="leaderboard",
        description="Affiche le classement Pokémon TCG"
    )
    @app_commands.describe(
        classement="Type de classement à afficher"
    )
    @app_commands.choices(
        classement=[
            app_commands.Choice(name="PokéCoins", value="coins"),
            app_commands.Choice(name="Niveau", value="level"),
            app_commands.Choice(name="Cartes totales", value="cards"),
            app_commands.Choice(name="Cartes uniques", value="unique"),
            app_commands.Choice(name="Valeur de collection", value="value"),
            app_commands.Choice(name="Boosters ouverts", value="boosters"),
        ]
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        classement: str = "value"
    ):

        await interaction.response.defer()

        users = get_all_users(limit=100)

        if not users:
            return await interaction.followup.send(
                "📭 Aucun joueur trouvé dans la base de données."
            )

        ranked_users = sorted(
            users,
            key=lambda user: get_user_score(user, classement),
            reverse=True
        )

        ranked_users = [
            user for user in ranked_users
            if get_user_score(user, classement) > 0
        ]

        if not ranked_users:
            return await interaction.followup.send(
                "📭 Aucun joueur à afficher dans ce classement."
            )

        top_users = ranked_users[:10]

        lines = []

        for index, user_data in enumerate(top_users, start=1):
            user_id = user_data.get("id")
            score = format_score(user_data, classement)

            lines.append(
                f"{get_rank_emoji(index)} <@{user_id}> — **{score}**"
            )

        embed = discord.Embed(
            title=get_leaderboard_title(classement),
            description="\n".join(lines),
            color=discord.Color.gold()
        )

        embed.set_footer(
            text="Top 10 des joueurs Pokémon TCG"
        )

        await interaction.followup.send(
            embed=embed
        )


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))