import discord

from discord import app_commands
from discord.ext import commands

from service.achievements import (
    ACHIEVEMENTS,
    check_achievements,
    get_all_achievements_status,
    get_unlocked_achievements,
)
from views.achievement_ui import build_new_achievements_embed

# ============================================================
# EMBED
# ============================================================




def build_new_achievements_embed(user, new_achievements) -> discord.Embed:

    embed = discord.Embed(
        title="🎉 Nouveaux succès débloqués !",
        description=f"{user.mention}, tu as débloqué de nouveaux succès.",
        color=discord.Color.green()
    )

    lines = []

    total_reward = 0

    for achievement in new_achievements:

        emoji = achievement.get("emoji", "🏆")
        name = achievement.get("name", "Succès")
        description = achievement.get("description", "")
        reward = achievement.get("reward", 0)

        total_reward += reward

        lines.append(
            f"{emoji} **{name}**\n"
            f"{description}\n"
            f"🎁 +**{reward} PokéCoins**"
        )

    embed.add_field(
        name="Succès",
        value="\n\n".join(lines),
        inline=False
    )

    embed.add_field(
        name="Récompense totale",
        value=f"🪙 **{total_reward} PokéCoins**",
        inline=False
    )

    return embed


# ============================================================
# COG
# ============================================================

class Achievements(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="achievements",
        description="Affiche tes succès Pokémon TCG"
    )
    async def achievements(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.defer()

        new_achievements = check_achievements(
            interaction.user.id
        )

        statuses = get_all_achievements_status(
            interaction.user.id
        )

        if new_achievements:
            await interaction.followup.send(
                embed=build_new_achievements_embed(
                    interaction.user,
                    new_achievements
                )
            )

        await interaction.followup.send(
            
        )


async def setup(bot):
    await bot.add_cog(Achievements(bot))