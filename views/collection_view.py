import discord

from service.inventory import (
    get_inventory_page,
    get_inventory_stats,
    format_inventory_page,
)


# ============================================================
# COLLECTION VIEW
# ============================================================

class CollectionView(discord.ui.View):

    def __init__(
        self,
        user_id,
        query: str = "",
        rarity: str = None,
        favorites_only: bool = False,
        sort: str = "name",
        page: int = 0
    ):
        super().__init__(timeout=180)

        self.user_id = str(user_id)
        self.query = query or ""
        self.rarity = rarity
        self.favorites_only = favorites_only
        self.sort = sort or "name"
        self.page = page

        self.refresh_items()

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ Cette collection ne t'appartient pas.",
                ephemeral=True
            )
            return False

        return True

    def get_page_data(self):

        return get_inventory_page(
            self.user_id,
            page=self.page,
            query=self.query,
            rarity=self.rarity,
            favorites_only=self.favorites_only,
            sort=self.sort
        )

    def build_embed(
        self,
        interaction: discord.Interaction = None
    ) -> discord.Embed:

        page_data = self.get_page_data()
        stats = get_inventory_stats(self.user_id)

        embed = discord.Embed(
            title="📚 Collection Pokémon TCG",
            description=format_inventory_page(page_data),
            color=discord.Color.blue()
        )

        embed.add_field(
            name="📊 Statistiques",
            value=(
                f"🃏 Total : **{stats['total_cards']}** cartes\n"
                f"🎴 Uniques : **{stats['unique_cards']}** cartes\n"
                f"🔁 Doublons : **{stats['duplicates']}**\n"
                f"⭐ Favoris : **{stats['favorites']}**\n"
                f"💎 Valeur : **{stats['value']}**"
            ),
            inline=False
        )

        rarity_text = (
            f"⚪ Communes : **{stats['rarities']['common']}**\n"
            f"🟢 Peu communes : **{stats['rarities']['uncommon']}**\n"
            f"🔵 Rares : **{stats['rarities']['rare']}**\n"
            f"✨ Holos : **{stats['rarities']['holo']}**\n"
            f"🌈 Ultras : **{stats['rarities']['ultra']}**\n"
            f"👑 Secrètes : **{stats['rarities']['secret']}**"
        )

        embed.add_field(
            name="🌟 Raretés",
            value=rarity_text,
            inline=False
        )

        filters = []

        if self.query:
            filters.append(f"Recherche : `{self.query}`")

        if self.rarity:
            filters.append(f"Rareté : `{self.rarity}`")

        if self.favorites_only:
            filters.append("Favoris uniquement")

        filters.append(f"Tri : `{self.sort}`")

        embed.set_footer(
            text=" · ".join(filters)
        )

        return embed

    def refresh_items(self):

        self.clear_items()

        page_data = self.get_page_data()

        previous_button = discord.ui.Button(
            label="⬅️ Précédent",
            style=discord.ButtonStyle.secondary,
            disabled=not page_data["has_previous"]
        )

        next_button = discord.ui.Button(
            label="Suivant ➡️",
            style=discord.ButtonStyle.secondary,
            disabled=not page_data["has_next"]
        )

        previous_button.callback = self.previous_page
        next_button.callback = self.next_page

        self.add_item(previous_button)
        self.add_item(next_button)

    async def previous_page(
        self,
        interaction: discord.Interaction
    ):

        if self.page > 0:
            self.page -= 1

        self.refresh_items()

        await interaction.response.edit_message(
            embed=self.build_embed(interaction),
            view=self
        )

    async def next_page(
        self,
        interaction: discord.Interaction
    ):

        self.page += 1

        self.refresh_items()

        await interaction.response.edit_message(
            embed=self.build_embed(interaction),
            view=self
        )

    async def on_timeout(self):

        for item in self.children:
            item.disabled = True