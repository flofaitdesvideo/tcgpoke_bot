import discord

from service.inventory import (
    get_card,
    is_favorite,
    toggle_favorite,
)


# ============================================================
# OUTILS
# ============================================================

def get_card_image_url(card):
    image = card.get("image")

    if not image:
        return None

    image = str(image)

    if image.endswith(".png") or image.endswith(".jpg") or image.endswith(".jpeg") or image.endswith(".webp"):
        return image

    return f"{image}/high.webp"


def build_card_embed(
    card,
    user: discord.User
) -> discord.Embed:

    name = card.get("name", "Carte inconnue")
    rarity = card.get("rarity", "Inconnue")
    rarity_emoji = card.get("rarity_emoji", "🎴")
    rarity_tier = card.get("rarity_tier", "common")
    value = card.get("value", 1)
    count = card.get("count", 1)

    set_data = card.get("set", {})
    set_name = set_data.get("name", "Extension inconnue")
    set_id = set_data.get("id", "unknown")

    types = card.get("types", [])

    if isinstance(types, list) and types:
        types_text = ", ".join(types)
    else:
        types_text = "Inconnu"

    embed = discord.Embed(
        title=f"{rarity_emoji} {name}",
        description=f"Carte de la collection de {user.mention}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="⭐ Infos",
        value=(
            f"Rareté : **{rarity}**\n"
            f"Tier : `{rarity_tier}`\n"
            f"Valeur : **{value}**\n"
            f"Copies : **x{count}**"
        ),
        inline=True
    )

    embed.add_field(
        name="📦 Extension",
        value=(
            f"Nom : **{set_name}**\n"
            f"ID : `{set_id}`"
        ),
        inline=True
    )

    embed.add_field(
        name="🧬 Type",
        value=types_text,
        inline=False
    )

    image_url = get_card_image_url(card)

    if image_url:
        embed.set_image(url=image_url)

    embed.set_footer(
        text=f"ID carte : {card.get('id', 'unknown')}"
    )

    return embed


# ============================================================
# VIEW CARD
# ============================================================

class CardView(discord.ui.View):

    def __init__(
        self,
        user_id,
        card_id
    ):
        super().__init__(timeout=180)

        self.user_id = str(user_id)
        self.card_id = str(card_id)

        self.refresh_items()

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ Cette carte ne t'appartient pas.",
                ephemeral=True
            )
            return False

        return True

    def refresh_items(self):

        self.clear_items()

        favorite = is_favorite(
            self.user_id,
            self.card_id
        )

        if favorite:
            label = "⭐ Retirer des favoris"
            style = discord.ButtonStyle.danger
        else:
            label = "⭐ Ajouter aux favoris"
            style = discord.ButtonStyle.success

        favorite_button = discord.ui.Button(
            label=label,
            style=style
        )

        favorite_button.callback = self.toggle_favorite_button

        self.add_item(favorite_button)

    async def toggle_favorite_button(
        self,
        interaction: discord.Interaction
    ):

        toggle_favorite(
            self.user_id,
            self.card_id
        )

        card = get_card(
            self.user_id,
            self.card_id
        )

        self.refresh_items()

        await interaction.response.edit_message(
            embed=build_card_embed(
                card,
                interaction.user
            ),
            view=self
        )

    async def on_timeout(self):

        for item in self.children:
            item.disabled = True