import discord

from service.trade import (
    complete_trade,
    format_trade_card,
)

from service.achievements import check_achievements
from views.achievement_ui import build_new_achievements_embed
from service.missions import record_mission_progress

# ============================================================
# EMBEDS
# ============================================================

def build_trade_embed(
    offerer: discord.Member,
    target: discord.Member,
    offer_card,
    requested_card
) -> discord.Embed:

    embed = discord.Embed(
        title="🤝 Proposition d'échange",
        description=(
            f"{offerer.mention} propose un échange à {target.mention}."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name=f"🎴 {offerer.display_name} donne",
        value=format_trade_card(offer_card),
        inline=True
    )

    embed.add_field(
        name=f"🎴 {target.display_name} donne",
        value=format_trade_card(requested_card),
        inline=True
    )

    embed.set_footer(
        text="Seul le joueur ciblé peut accepter ou refuser."
    )

    return embed


def build_trade_success_embed(
    offerer_id,
    target_id,
    offer_card,
    requested_card
) -> discord.Embed:

    embed = discord.Embed(
        title="✅ Échange terminé !",
        description=(
            f"L'échange entre <@{offerer_id}> et <@{target_id}> est validé."
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name=f"🎴 <@{target_id}> reçoit",
        value=format_trade_card(offer_card),
        inline=True
    )

    embed.add_field(
        name=f"🎴 <@{offerer_id}> reçoit",
        value=format_trade_card(requested_card),
        inline=True
    )

    embed.set_footer(
        text="Les collections ont été mises à jour."
    )

    return embed


def build_trade_cancel_embed(reason: str) -> discord.Embed:

    embed = discord.Embed(
        title="❌ Échange annulé",
        description=reason,
        color=discord.Color.red()
    )

    return embed


# ============================================================
# VIEW TRADE
# ============================================================

class TradeView(discord.ui.View):

    def __init__(
        self,
        offerer_id,
        target_id,
        offer_card_id,
        requested_card_id
    ):
        super().__init__(timeout=180)

        self.offerer_id = str(offerer_id)
        self.target_id = str(target_id)
        self.offer_card_id = str(offer_card_id)
        self.requested_card_id = str(requested_card_id)

        self.finished = False

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        user_id = str(interaction.user.id)

        if user_id not in [self.offerer_id, self.target_id]:
            await interaction.response.send_message(
                "❌ Tu ne participes pas à cet échange.",
                ephemeral=True
            )
            return False

        return True

    def disable_all(self):

        for item in self.children:
            item.disabled = True

    @discord.ui.button(
        label="✅ Accepter",
        style=discord.ButtonStyle.success
    )
    async def accept_trade(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if self.finished:
            return await interaction.response.send_message(
                "❌ Cet échange est déjà terminé.",
                ephemeral=True
            )

        if str(interaction.user.id) != self.target_id:
            return await interaction.response.send_message(
                "❌ Seul le joueur ciblé peut accepter cet échange.",
                ephemeral=True
            )

        await interaction.response.defer()

        result = complete_trade(
            self.offerer_id,
            self.target_id,
            self.offer_card_id,
            self.requested_card_id
        )

        self.finished = True
        self.disable_all()

        if not result["success"]:
            embed = build_trade_cancel_embed(
                result["reason"]
            )

            return await interaction.edit_original_response(
                embed=embed,
                view=self
            )

        embed = build_trade_success_embed(
            self.offerer_id,
            self.target_id,
            result["offer_card"],
            result["requested_card"]
        )

        await interaction.edit_original_response(
            embed=embed,
            view=self
        )
        record_mission_progress(
            self.offerer_id,
            "trade_completed",
            1
        )

        record_mission_progress(
            self.target_id,
            "trade_completed",
            1
        )

        target_achievements = check_achievements(
            self.target_id
        )

        offerer_achievements = check_achievements(
            self.offerer_id
        )

        if target_achievements:
            await interaction.followup.send(
                embed=build_new_achievements_embed(
                    self.target_id,
                    target_achievements
                )
            )

        if offerer_achievements:
            await interaction.followup.send(
                embed=build_new_achievements_embed(
                    self.offerer_id,
                    offerer_achievements
                )
            )

    @discord.ui.button(
        label="❌ Refuser",
        style=discord.ButtonStyle.danger
    )
    async def refuse_trade(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if self.finished:
            return await interaction.response.send_message(
                "❌ Cet échange est déjà terminé.",
                ephemeral=True
            )

        if str(interaction.user.id) != self.target_id:
            return await interaction.response.send_message(
                "❌ Seul le joueur ciblé peut refuser cet échange.",
                ephemeral=True
            )

        self.finished = True
        self.disable_all()

        embed = build_trade_cancel_embed(
            f"{interaction.user.mention} a refusé l'échange."
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    @discord.ui.button(
        label="🚫 Annuler",
        style=discord.ButtonStyle.secondary
    )
    async def cancel_trade(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if self.finished:
            return await interaction.response.send_message(
                "❌ Cet échange est déjà terminé.",
                ephemeral=True
            )

        if str(interaction.user.id) != self.offerer_id:
            return await interaction.response.send_message(
                "❌ Seul le créateur peut annuler cet échange.",
                ephemeral=True
            )

        self.finished = True
        self.disable_all()

        embed = build_trade_cancel_embed(
            f"{interaction.user.mention} a annulé l'échange."
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    async def on_timeout(self):

        self.finished = True
        self.disable_all()