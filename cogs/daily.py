import time
import discord

from discord import app_commands
from discord.ext import commands

from service.database import (
    get_user,
    update_user,
    add_coins,
    add_xp,
)
from service.achievements import check_achievements
from views.achievement_ui import build_new_achievements_embed
from service.database import update_user_profile
DAILY_COINS = 500
DAILY_XP = 50
DAILY_COOLDOWN = 60 * 60 * 24


def format_time_left(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}min"

    return f"{minutes}min"


class Daily(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="daily",
        description="Récupère ta récompense quotidienne"
    )
    async def daily(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.defer()

        user_id = interaction.user.id
        user = await update_user_profile(interaction.user)

        now = int(time.time())
        last_daily = int(user.get("daily", 0))

        elapsed = now - last_daily

        if elapsed < DAILY_COOLDOWN:
            remaining = DAILY_COOLDOWN - elapsed

            embed = discord.Embed(
                title="⏳ Récompense déjà récupérée",
                description=(
                    f"Tu as déjà récupéré ta récompense quotidienne.\n\n"
                    f"Reviens dans **{format_time_left(remaining)}**."
                ),
                color=discord.Color.orange()
            )

            return await interaction.followup.send(
                embed=embed
            )

        add_coins(
            user_id,
            DAILY_COINS
        )

        add_xp(
            user_id,
            DAILY_XP
        )

        update_user(
            user_id,
            {
                "daily": now
            }
        )

        embed = discord.Embed(
            title="🎁 Récompense quotidienne récupérée !",
            description=(
                f"{interaction.user.mention}, tu as reçu :\n\n"
                f"🪙 **{DAILY_COINS} PokéCoins**\n"
                f"⚡ **{DAILY_XP} XP**"
            ),
            color=discord.Color.green()
        )

        embed.set_footer(
            text="Reviens demain pour récupérer une nouvelle récompense."
        )

        await interaction.followup.send(
            embed=embed
        )

        new_achievements = check_achievements(
            interaction.user.id
        )

        if new_achievements:
            await interaction.followup.send(
                embed=build_new_achievements_embed(
                    interaction.user,
                    new_achievements
                )
            )


async def setup(bot):
    await bot.add_cog(Daily(bot))