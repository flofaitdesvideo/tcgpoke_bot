import discord

from service.missions import (
    get_all_mission_statuses,
    claim_completed_missions,
)


def build_missions_embed(user, statuses) -> discord.Embed:

    completed = len([
        mission for mission in statuses
        if mission["completed"]
    ])

    claimed = len([
        mission for mission in statuses
        if mission["claimed"]
    ])

    embed = discord.Embed(
        title=f"🎯 Missions quotidiennes de {user.display_name}",
        description=(
            f"Progression : **{completed}/{len(statuses)}** terminées\n"
            f"Récompenses récupérées : **{claimed}/{len(statuses)}**"
        ),
        color=discord.Color.blue()
    )

    for mission in statuses:

        emoji = mission["emoji"]
        name = mission["name"]
        description = mission["description"]
        progress = mission["progress"]
        target = mission["target"]

        if mission["claimed"]:
            status = "✅ Récompense récupérée"
        elif mission["completed"]:
            status = "🎁 Récompense disponible"
        else:
            status = "⏳ En cours"

        embed.add_field(
            name=f"{emoji} {name}",
            value=(
                f"{description}\n"
                f"Progression : **{progress}/{target}**\n"
                f"Récompense : 🪙 **{mission['coins']}** "
                f"· ⚡ **{mission['xp']} XP** "
                f"· 💎 **{mission['gems']}**\n"
                f"{status}"
            ),
            inline=False
        )

    embed.set_footer(
        text="Les missions changent chaque jour."
    )

    if user.display_avatar:
        embed.set_thumbnail(
            url=user.display_avatar.url
        )

    return embed


class MissionsView(discord.ui.View):

    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = str(user_id)

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ Ces missions ne t'appartiennent pas.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="🎁 Récupérer les récompenses",
        style=discord.ButtonStyle.success
    )
    async def claim_rewards(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer()

        result = claim_completed_missions(
            interaction.user.id
        )

        if not result["claimed"]:
            return await interaction.followup.send(
                "❌ Tu n'as aucune récompense de mission à récupérer.",
                ephemeral=True
            )

        statuses = get_all_mission_statuses(
            interaction.user.id
        )

        reward_embed = discord.Embed(
            title="🎁 Récompenses récupérées !",
            description=(
                f"🪙 PokéCoins : **+{result['coins']}**\n"
                f"⚡ XP : **+{result['xp']}**\n"
                f"💎 Gems : **+{result['gems']}**"
            ),
            color=discord.Color.green()
        )

        await interaction.followup.send(
            embed=reward_embed
        )

        await interaction.edit_original_response(
            embed=build_missions_embed(
                interaction.user,
                statuses
            ),
            view=self
        )

    @discord.ui.button(
        label="🔄 Actualiser",
        style=discord.ButtonStyle.secondary
    )
    async def refresh(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        statuses = get_all_mission_statuses(
            interaction.user.id
        )

        await interaction.response.edit_message(
            embed=build_missions_embed(
                interaction.user,
                statuses
            ),
            view=self
        )