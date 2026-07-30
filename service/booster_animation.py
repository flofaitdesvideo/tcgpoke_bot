
import asyncio
from typing import Any, Dict, List, Optional

import discord

from service.card_format import format_card_embed
from service.booster import get_booster_summary


# ============================================================
# CONFIGURATION
# ============================================================

REVEAL_DELAYS = {
    "common": 0.65,
    "uncommon": 0.8,
    "rare": 1.1,
    "holo": 1.4,
    "ultra": 1.8,
    "secret": 2.4,
}

RARITY_COLORS = {
    "common": discord.Color.light_grey(),
    "uncommon": discord.Color.green(),
    "rare": discord.Color.blue(),
    "holo": discord.Color.teal(),
    "ultra": discord.Color.purple(),
    "secret": discord.Color.gold(),
}

RARITY_LABELS = {
    "common": "Commune",
    "uncommon": "Peu commune",
    "rare": "Rare",
    "holo": "Holographique",
    "ultra": "Ultra rare",
    "secret": "Secrète",
}

RARITY_EMOJIS = {
    "common": "⚪",
    "uncommon": "🟢",
    "rare": "🔵",
    "holo": "✨",
    "ultra": "🌈",
    "secret": "👑",
}


# ============================================================
# OUTILS
# ============================================================

def get_card_tier(card: Dict[str, Any]) -> str:
    """
    Récupère la rareté simplifiée de la carte.
    """

    tier = str(card.get("rarity_tier", "common")).lower()

    if tier not in RARITY_COLORS:
        return "common"

    return tier


def get_card_image(
    card: Dict[str, Any],
    formatted_card: Dict[str, Any]
) -> Optional[str]:
    """
    Récupère l'image HD de la carte.

    TCGdex retourne parfois une URL sans extension :
    https://assets.tcgdex.net/fr/sv/sv01/001

    Il faut alors ajouter :
    /high.webp
    """

    image = formatted_card.get("image") or card.get("image")

    if not image:
        return None

    image = str(image)

    if image.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return image

    return f"{image}/high.webp"


# ============================================================
# EMBED D'UNE CARTE
# ============================================================

def create_card_embed(
    card: Dict[str, Any],
    index: int,
    total: int,
    reveal: bool = False
) -> discord.Embed:
    """
    Crée l'embed Discord d'une carte.
    """

    formatted_card = format_card_embed(card)

    tier = get_card_tier(card)

    emoji = (
        card.get("rarity_emoji")
        or RARITY_EMOJIS.get(tier, "⚪")
    )

    rarity = (
        card.get("rarity")
        or RARITY_LABELS.get(tier, "Commune")
    )

    value = int(card.get("value", 0) or 0)

    card_name = (
        formatted_card.get("title")
        or card.get("name")
        or "Carte inconnue"
    )

    original_description = (
        formatted_card.get("description")
        or ""
    )

    # Message spécial pendant la révélation
    if reveal and tier == "secret":
        title = f"👑 CARTE SECRÈTE ! — {card_name}"

    elif reveal and tier == "ultra":
        title = f"🌈 ULTRA RARE ! — {card_name}"

    elif reveal and tier == "holo":
        title = f"✨ CARTE HOLOGRAPHIQUE ! — {card_name}"

    else:
        title = f"{emoji} {card_name}"

    description_parts = []

    if original_description:
        description_parts.append(original_description)

    description_parts.append(f"**Rareté :** {rarity}")
    description_parts.append(
        f"**Valeur :** {value} point{'s' if value != 1 else ''}"
    )

    set_data = card.get("set") or {}
    set_name = set_data.get("name")

    if set_name:
        description_parts.append(
            f"**Extension :** {set_name}"
        )

    local_id = card.get("local_id")

    if local_id:
        description_parts.append(
            f"**Numéro :** {local_id}"
        )

    embed = discord.Embed(
        title=title,
        description="\n".join(description_parts),
        color=RARITY_COLORS.get(
            tier,
            discord.Color.light_grey()
        )
    )

    image = get_card_image(card, formatted_card)

    if image:
        embed.set_image(url=image)

    else:
        embed.add_field(
            name="🖼️ Image indisponible",
            value=(
                "Aucune image n'est disponible "
                "pour cette carte."
            ),
            inline=False
        )

    embed.set_footer(
        text=(
            f"Carte {index + 1}/{total} • "
            "Utilise les boutons pour naviguer"
        )
    )

    return embed


# ============================================================
# EMBED DU RÉSUMÉ
# ============================================================

def create_summary_embed(
    cards: List[Dict[str, Any]]
) -> discord.Embed:
    """
    Crée le résumé final du booster.
    """

    summary = get_booster_summary(cards)

    best_card = summary.get("best_card")

    embed = discord.Embed(
        title="🎉 Booster terminé !",
        description=(
            f"**{summary.get('total', len(cards))} cartes obtenues**\n"
            f"💰 Valeur totale : "
            f"**{summary.get('value', 0)} points**"
        ),
        color=discord.Color.green()
    )

    rarity_counts = [
        (
            "👑 Secrètes",
            summary.get("secret", 0)
        ),
        (
            "🌈 Ultra rares",
            summary.get("ultra", 0)
        ),
        (
            "✨ Holographiques",
            summary.get("holo", 0)
        ),
        (
            "🔵 Rares",
            summary.get("rare", 0)
        ),
        (
            "🟢 Peu communes",
            summary.get("uncommon", 0)
        ),
        (
            "⚪ Communes",
            summary.get("common", 0)
        ),
    ]

    rarity_text = "\n".join(
        f"{label} : **{amount}**"
        for label, amount in rarity_counts
    )

    embed.add_field(
        name="📊 Répartition",
        value=rarity_text,
        inline=False
    )

    if best_card:
        best_name = best_card.get(
            "name",
            "Carte inconnue"
        )

        best_rarity = best_card.get(
            "rarity",
            "Rareté inconnue"
        )

        best_value = best_card.get(
            "value",
            0
        )

        embed.add_field(
            name="⭐ Meilleure carte",
            value=(
                f"**{best_name}**\n"
                f"{best_rarity} • "
                f"{best_value} points"
            ),
            inline=False
        )

        formatted_best_card = format_card_embed(
            best_card
        )

        best_image = get_card_image(
            best_card,
            formatted_best_card
        )

        if best_image:
            embed.set_image(url=best_image)

    embed.set_footer(
        text=(
            "Clique sur « Voir les cartes » "
            "pour revoir le booster"
        )
    )

    return embed


# ============================================================
# BOUTONS INTERACTIFS
# ============================================================

class BoosterView(discord.ui.View):

    def __init__(
        self,
        owner_id: int,
        cards: List[Dict[str, Any]],
        start_index: int = 0,
        timeout: float = 180
    ):
        super().__init__(timeout=timeout)

        self.owner_id = owner_id
        self.cards = cards

        self.index = max(
            0,
            min(start_index, len(cards) - 1)
        )

        self.showing_summary = False

        self.message: Optional[discord.Message] = None

        self.update_buttons()


    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:
        """
        Empêche les autres joueurs d'utiliser les boutons.
        """

        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                (
                    "❌ Seule la personne qui a ouvert "
                    "ce booster peut utiliser ces boutons."
                ),
                ephemeral=True
            )

            return False

        return True


    def update_buttons(self) -> None:
        """
        Active ou désactive les boutons selon la page.
        """

        self.previous_button.disabled = (
            self.showing_summary
            or self.index <= 0
        )

        self.next_button.disabled = (
            self.showing_summary
            or self.index >= len(self.cards) - 1
        )

        self.summary_button.disabled = (
            self.showing_summary
        )

        self.cards_button.disabled = (
            not self.showing_summary
        )

        self.counter_button.label = (
            f"{self.index + 1}/{len(self.cards)}"
        )


    async def show_card(
        self,
        interaction: discord.Interaction
    ) -> None:
        """
        Affiche la carte actuellement sélectionnée.
        """

        self.showing_summary = False

        self.update_buttons()

        embed = create_card_embed(
            self.cards[self.index],
            self.index,
            len(self.cards)
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )


    @discord.ui.button(
        emoji="⬅️",
        label="Précédente",
        style=discord.ButtonStyle.secondary
    )
    async def previous_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ) -> None:
        self.index = max(
            0,
            self.index - 1
        )

        await self.show_card(interaction)


    @discord.ui.button(
        label="1/10",
        style=discord.ButtonStyle.secondary,
        disabled=True
    )
    async def counter_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ) -> None:
        """
        Bouton uniquement visuel.
        """

        await interaction.response.defer()


    @discord.ui.button(
        emoji="➡️",
        label="Suivante",
        style=discord.ButtonStyle.primary
    )
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ) -> None:
        self.index = min(
            len(self.cards) - 1,
            self.index + 1
        )

        await self.show_card(interaction)


    @discord.ui.button(
        emoji="📊",
        label="Résumé",
        style=discord.ButtonStyle.success
    )
    async def summary_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ) -> None:
        self.showing_summary = True

        self.update_buttons()

        await interaction.response.edit_message(
            embed=create_summary_embed(
                self.cards
            ),
            view=self
        )


    @discord.ui.button(
        emoji="🎴",
        label="Voir les cartes",
        style=discord.ButtonStyle.primary,
        disabled=True
    )
    async def cards_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ) -> None:
        await self.show_card(interaction)


    @discord.ui.button(
        emoji="❌",
        label="Fermer",
        style=discord.ButtonStyle.danger
    )
    async def close_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ) -> None:
        """
        Désactive tous les boutons.
        """

        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(
            view=self
        )

        self.stop()


    async def on_timeout(self) -> None:
        """
        Désactive les boutons après trois minutes.
        """

        for child in self.children:
            child.disabled = True

        if not self.message:
            return

        try:
            await self.message.edit(
                view=self
            )

        except (
            discord.NotFound,
            discord.HTTPException
        ):
            pass


# ============================================================
# ANIMATION DU BOOSTER
# ============================================================

async def play_booster_animation(
    interaction: discord.Interaction,
    cards: List[Dict[str, Any]]
) -> Optional[discord.Message]:
    """
    Anime l'ouverture du booster.

    Ensuite, le joueur peut revoir les cartes
    avec les boutons Discord.
    """

    if not cards:
        return await interaction.followup.send(
            (
                "❌ Impossible d'ouvrir le booster : "
                "aucune carte n'a été reçue."
            ),
            ephemeral=True
        )

    opening_embed = discord.Embed(
        title="🎁 Ouverture du booster...",
        description=(
            "Préparation des cartes...\n"
            "`[░░░░░░░░░░] 0%`"
        ),
        color=discord.Color.gold()
    )

    message = await interaction.followup.send(
        embed=opening_embed,
        wait=True
    )

    # Première animation
    progress_steps = [
        (
            "Découpe de l'emballage... ✂️",
            "[██░░░░░░░░] 20%"
        ),
        (
            "Les cartes brillent... ✨",
            "[█████░░░░░] 50%"
        ),
        (
            "Le booster est prêt ! 🎴",
            "[██████████] 100%"
        ),
    ]

    for text, progress_bar in progress_steps:
        await asyncio.sleep(0.65)

        opening_embed.description = (
            f"{text}\n"
            f"`{progress_bar}`"
        )

        await message.edit(
            embed=opening_embed
        )

    # Révélation automatique des cartes
    for index, card in enumerate(cards):
        tier = get_card_tier(card)

        delay = REVEAL_DELAYS.get(
            tier,
            0.65
        )

        await asyncio.sleep(delay)

        card_embed = create_card_embed(
            card,
            index,
            len(cards),
            reveal=True
        )

        await message.edit(
            embed=card_embed,
            view=None
        )

    await asyncio.sleep(1)

    # Création de la navigation finale
    view = BoosterView(
        owner_id=interaction.user.id,
        cards=cards,
        start_index=len(cards) - 1,
        timeout=180
    )

    view.showing_summary = True
    view.update_buttons()
    view.message = message

    await message.edit(
        embed=create_summary_embed(cards),
        view=view
    )

    return message