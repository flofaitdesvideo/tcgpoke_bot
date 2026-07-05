import math
import discord

from service.booster import (
    open_booster,
    get_booster_summary,
    format_card_line,
)

from service.inventory import add_booster_cards
from service.achievements import check_achievements
from service.missions import record_mission_progress

from views.achievement_ui import build_new_achievements_embed

from service.cooldowns import (
    get_booster_cooldown_remaining,
    set_booster_cooldown,
    format_cooldown,
)
PAGE_SIZE = 25


# ============================================================
# EMBED BOOSTER
# ============================================================

def build_booster_embed(
    interaction: discord.Interaction,
    cards,
    set_name: str
) -> discord.Embed:

    summary = get_booster_summary(cards)

    embed = discord.Embed(
        title="🎁 Booster ouvert !",
        description=f"{interaction.user.mention} a ouvert un booster **{set_name}**.",
        color=discord.Color.gold()
    )

    best_card = summary.get("best_card")

    if best_card:
        embed.add_field(
            name="🌟 Meilleure carte",
            value=format_card_line(best_card),
            inline=False
        )

        image = best_card.get("image")

        if image:
            embed.set_image(url=image)

    lines = []

    for card in cards:
        lines.append(format_card_line(card))

    text = "\n".join(lines)

    if len(text) > 1024:
        text = text[:1000] + "\n..."

    embed.add_field(
        name="🃏 Cartes obtenues",
        value=text or "Aucune carte.",
        inline=False
    )

    embed.add_field(
        name="📊 Résumé",
        value=(
            f"⚪ Communes : **{summary['common']}**\n"
            f"🟢 Peu communes : **{summary['uncommon']}**\n"
            f"🔵 Rares : **{summary['rare']}**\n"
            f"✨ Holos : **{summary['holo']}**\n"
            f"🌈 Ultras : **{summary['ultra']}**\n"
            f"👑 Secrètes : **{summary['secret']}**\n"
            f"💎 Valeur : **{summary['value']}**"
        ),
        inline=False
    )

    embed.set_footer(
        text="Les cartes ont été ajoutées à ta collection."
    )

    return embed


# ============================================================
# SELECT EXTENSION
# ============================================================

class ExtensionSelect(discord.ui.Select):

    def __init__(self, parent_view):

        self.parent_view = parent_view

        start = parent_view.page * PAGE_SIZE
        end = start + PAGE_SIZE

        current_sets = parent_view.sets[start:end]

        options = []

        for extension in current_sets:

            set_id = str(extension.get("id", "unknown"))
            name = str(extension.get("name", set_id))

            serie = extension.get("serie", "")

            if isinstance(serie, dict):
                serie_name = serie.get("name", "")
            else:
                serie_name = str(serie) if serie else ""

            description = f"ID: {set_id}"

            if serie_name:
                description = f"{serie_name} · {set_id}"

            options.append(
                discord.SelectOption(
                    label=name[:100],
                    value=set_id[:100],
                    description=description[:100],
                    emoji="🎴"
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="Aucune extension",
                    value="__none__",
                    description="Aucune extension disponible"
                )
            )

        super().__init__(
            placeholder=(
                f"🎁 Choisis une extension "
                f"({parent_view.page + 1}/{parent_view.max_page + 1})"
            ),
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        remaining = get_booster_cooldown_remaining(
            interaction.user.id
        )

        if remaining > 0:
            return await interaction.followup.send(
                f"⏳ Tu as déjà ouvert ton booster gratuit.\n"
                f"Tu pourras en rouvrir un dans **{format_cooldown(remaining)}**.",
                ephemeral=True
            )
        set_id = self.values[0]

        if set_id == "__none__":
            return await interaction.response.send_message(
                "❌ Aucune extension disponible.",
                ephemeral=True
            )



        selected_set = self.parent_view.get_set_by_id(set_id)

        if selected_set:
            set_name = selected_set.get("name", set_id)
        else:
            set_name = set_id

        cards = await open_booster(set_id)

        if not cards:
            return await interaction.followup.send(
                "❌ Cette extension est vide ou indisponible."
            )

        added_cards = add_booster_cards(
            interaction.user.id,
            cards,
            xp_reward=25
        )
        set_booster_cooldown(
            interaction.user.id
        )
        record_mission_progress(
            interaction.user.id,
            "booster_opened",
            1
        )

        record_mission_progress(
            interaction.user.id,
            "card_collected",
            len(added_cards)
        )

        embed = build_booster_embed(
            interaction,
            added_cards,
            set_name
        )

        await interaction.followup.send(embed=embed)

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


# ============================================================
# VIEW EXTENSIONS
# ============================================================

class ExtensionView(discord.ui.View):

    def __init__(self, sets):

        super().__init__(timeout=180)

        self.sets = sets or []
        self.page = 0

        self.max_page = max(
            0,
            math.ceil(len(self.sets) / PAGE_SIZE) - 1
        )

        self.refresh_items()

    def get_set_by_id(self, set_id: str):

        for extension in self.sets:
            if str(extension.get("id")) == str(set_id):
                return extension

        return None

    def refresh_items(self):

        self.clear_items()

        self.add_item(
            ExtensionSelect(self)
        )

        previous_button = discord.ui.Button(
            label="⬅️ Précédent",
            style=discord.ButtonStyle.secondary,
            disabled=self.page <= 0
        )

        next_button = discord.ui.Button(
            label="Suivant ➡️",
            style=discord.ButtonStyle.secondary,
            disabled=self.page >= self.max_page
        )

        previous_button.callback = self.previous_page
        next_button.callback = self.next_page

        self.add_item(previous_button)
        self.add_item(next_button)

    async def previous_page(self, interaction: discord.Interaction):

        if self.page > 0:
            self.page -= 1

        self.refresh_items()

        await interaction.response.edit_message(
            content=(
                f"🎁 Choisis ton extension "
                f"— page **{self.page + 1}/{self.max_page + 1}**"
            ),
            view=self
        )

    async def next_page(self, interaction: discord.Interaction):

        if self.page < self.max_page:
            self.page += 1

        self.refresh_items()

        await interaction.response.edit_message(
            content=(
                f"🎁 Choisis ton extension "
                f"— page **{self.page + 1}/{self.max_page + 1}**"
            ),
            view=self
        )

    async def on_timeout(self):

        for item in self.children:
            item.disabled = True