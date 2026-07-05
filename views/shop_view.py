import discord

from service.database import (
    get_user,
    remove_coins,
    add_coins,
)

from service.booster import (
    open_booster,
    open_random_booster,
    get_booster_summary,
    format_card_line,
)

from service.inventory import add_booster_cards
from service.missions import record_mission_progress
from service.achievements import check_achievements
from views.achievement_ui import build_new_achievements_embed


RANDOM_BOOSTER_PRICE = 300
TRIPLE_BOOSTER_PRICE = 800


def build_shop_embed(user_data, selected_set_name=None) -> discord.Embed:
    coins = user_data.get("coins", 0)
    gems = user_data.get("gems", 0)

    embed = discord.Embed(
        title="🛒 Boutique Pokémon TCG",
        description=(
            "Bienvenue dans la boutique !\n\n"
            f"Extension sélectionnée : **{selected_set_name or 'Aléatoire'}**"
        ),
        color=discord.Color.green()
    )

    embed.add_field(
        name="💰 Ton argent",
        value=(
            f"🪙 PokéCoins : **{coins}**\n"
            f"💎 Gems : **{gems}**"
        ),
        inline=False
    )

    embed.add_field(
        name="🎁 Acheter 1 booster",
        value=(
            f"Prix : **{RANDOM_BOOSTER_PRICE} PokéCoins**\n"
            "Contient **10 cartes**."
        ),
        inline=False
    )

    embed.add_field(
        name="📦 Acheter pack x3",
        value=(
            f"Prix : **{TRIPLE_BOOSTER_PRICE} PokéCoins**\n"
            "Contient **3 boosters**, soit **30 cartes** au total."
        ),
        inline=False
    )

    embed.set_footer(text="Utilise les boutons pour acheter.")

    return embed


def build_booster_purchase_embed(
    interaction: discord.Interaction,
    cards,
    price: int,
    set_name: str = "Aléatoire"
) -> discord.Embed:

    summary = get_booster_summary(cards)
    best_card = summary.get("best_card")

    embed = discord.Embed(
        title="🎁 Booster acheté et ouvert !",
        description=(
            f"{interaction.user.mention}, tu as dépensé "
            f"**{price} PokéCoins**.\n\n"
            f"Extension : **{set_name}**"
        ),
        color=discord.Color.gold()
    )

    if best_card:
        embed.add_field(
            name="🌟 Meilleure carte",
            value=format_card_line(best_card),
            inline=False
        )

        if best_card.get("image"):
            embed.set_image(url=best_card["image"])

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

    embed.set_footer(text="Les cartes ont été ajoutées à ta collection.")

    return embed


def build_multi_booster_embed(
    interaction: discord.Interaction,
    boosters_results,
    price: int,
    boosters_count: int,
    set_name: str = "Aléatoire"
) -> discord.Embed:

    all_cards = []

    for booster_cards in boosters_results:
        all_cards.extend(booster_cards)

    total_summary = get_booster_summary(all_cards)
    best_card = total_summary.get("best_card")

    embed = discord.Embed(
        title=f"📦 Pack x{boosters_count} boosters acheté !",
        description=(
            f"{interaction.user.mention}, tu as dépensé "
            f"**{price} PokéCoins**.\n\n"
            f"Extension : **{set_name}**\n"
            f"Total : **{len(all_cards)} cartes**"
        ),
        color=discord.Color.gold()
    )

    if best_card:
        embed.add_field(
            name="🌟 Meilleure carte du pack",
            value=format_card_line(best_card),
            inline=False
        )

        if best_card.get("image"):
            embed.set_image(url=best_card["image"])

    for index, booster_cards in enumerate(boosters_results, start=1):
        summary = get_booster_summary(booster_cards)
        booster_best = summary.get("best_card")

        rare_cards = [
            card for card in booster_cards
            if card.get("rarity_tier") in ["rare", "holo", "ultra", "secret"]
        ]

        lines = []

        if booster_best:
            lines.append(
                f"🌟 Meilleure : {format_card_line(booster_best)}"
            )

        if rare_cards:
            lines.append("")
            lines.append("Cartes rares :")

            for card in rare_cards[:5]:
                lines.append(format_card_line(card))

        lines.append("")
        lines.append(
            f"⚪ {summary['common']} · "
            f"🟢 {summary['uncommon']} · "
            f"🔵 {summary['rare']} · "
            f"✨ {summary['holo']} · "
            f"🌈 {summary['ultra']} · "
            f"👑 {summary['secret']}"
        )

        lines.append(f"💎 Valeur : **{summary['value']}**")

        text = "\n".join(lines)

        if len(text) > 1024:
            text = text[:1000] + "\n..."

        embed.add_field(
            name=f"🎁 Booster {index}",
            value=text or "Aucune carte.",
            inline=False
        )

    embed.add_field(
        name="📊 Résumé total du pack",
        value=(
            f"⚪ Communes : **{total_summary['common']}**\n"
            f"🟢 Peu communes : **{total_summary['uncommon']}**\n"
            f"🔵 Rares : **{total_summary['rare']}**\n"
            f"✨ Holos : **{total_summary['holo']}**\n"
            f"🌈 Ultras : **{total_summary['ultra']}**\n"
            f"👑 Secrètes : **{total_summary['secret']}**\n"
            f"💎 Valeur totale : **{total_summary['value']}**"
        ),
        inline=False
    )

    embed.set_footer(text="Les cartes ont été ajoutées à ta collection.")

    return embed


class ShopView(discord.ui.View):

    def __init__(self, user_id, set_id=None, set_name=None):
        super().__init__(timeout=180)
        self.user_id = str(user_id)
        self.set_id = set_id
        self.set_name = set_name or "Aléatoire"

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ Cette boutique ne t'appartient pas.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="🎁 Acheter 1 booster",
        style=discord.ButtonStyle.success
    )
    async def buy_random_booster(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer()

        user_id = interaction.user.id
        user = get_user(user_id)
        coins = user.get("coins", 0)

        if coins < RANDOM_BOOSTER_PRICE:
            return await interaction.followup.send(
                f"❌ Tu n'as pas assez de PokéCoins.\n"
                f"Prix : **{RANDOM_BOOSTER_PRICE}**\n"
                f"Tu as : **{coins}**",
                ephemeral=True
            )

        if self.set_id:
            cards = await open_booster(self.set_id)
        else:
            cards = await open_random_booster()

        if not cards:
            return await interaction.followup.send(
                "❌ Impossible d'ouvrir un booster pour le moment.",
                ephemeral=True
            )

        success = remove_coins(
            user_id,
            RANDOM_BOOSTER_PRICE
        )

        if not success:
            return await interaction.followup.send(
                "❌ Paiement refusé.",
                ephemeral=True
            )

        added_cards = add_booster_cards(
            user_id,
            cards,
            xp_reward=25
        )

        record_mission_progress(
            user_id,
            "booster_opened",
            1
        )

        record_mission_progress(
            user_id,
            "card_collected",
            len(added_cards)
        )

        embed = build_booster_purchase_embed(
            interaction,
            added_cards,
            RANDOM_BOOSTER_PRICE,
            set_name=self.set_name
        )

        await interaction.followup.send(embed=embed)

        new_achievements = check_achievements(user_id)

        if new_achievements:
            await interaction.followup.send(
                embed=build_new_achievements_embed(
                    interaction.user,
                    new_achievements
                )
            )

    @discord.ui.button(
        label="📦 Acheter pack x3",
        style=discord.ButtonStyle.primary
    )
    async def buy_triple_booster(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer()

        user_id = interaction.user.id
        user = get_user(user_id)
        coins = user.get("coins", 0)

        if coins < TRIPLE_BOOSTER_PRICE:
            return await interaction.followup.send(
                f"❌ Tu n'as pas assez de PokéCoins.\n"
                f"Prix : **{TRIPLE_BOOSTER_PRICE}**\n"
                f"Tu as : **{coins}**",
                ephemeral=True
            )

        success = remove_coins(
            user_id,
            TRIPLE_BOOSTER_PRICE
        )

        if not success:
            return await interaction.followup.send(
                "❌ Paiement refusé.",
                ephemeral=True
            )

        await interaction.followup.send(
            f"📦 Ouverture du pack x3 **{self.set_name}** en cours..."
        )

        boosters_results = []
        all_cards = []

        try:
            for _ in range(3):

                if self.set_id:
                    cards = await open_booster(self.set_id)
                else:
                    cards = await open_random_booster()

                if cards:
                    boosters_results.append(cards)
                    all_cards.extend(cards)

        except Exception as e:
            add_coins(
                user_id,
                TRIPLE_BOOSTER_PRICE
            )

            return await interaction.followup.send(
                f"❌ Erreur pendant l'ouverture du pack x3.\n"
                f"Tu as été remboursé de **{TRIPLE_BOOSTER_PRICE} PokéCoins**.\n\n"
                f"Erreur : `{e}`",
                ephemeral=True
            )

        if not all_cards:
            add_coins(
                user_id,
                TRIPLE_BOOSTER_PRICE
            )

            return await interaction.followup.send(
                f"❌ Impossible d'ouvrir les boosters pour le moment.\n"
                f"Tu as été remboursé de **{TRIPLE_BOOSTER_PRICE} PokéCoins**.",
                ephemeral=True
            )

        added_cards = add_booster_cards(
            user_id,
            all_cards,
            xp_reward=75
        )

        record_mission_progress(
            user_id,
            "booster_opened",
            3
        )

        record_mission_progress(
            user_id,
            "card_collected",
            len(added_cards)
        )

        embed = build_multi_booster_embed(
            interaction,
            boosters_results,
            TRIPLE_BOOSTER_PRICE,
            boosters_count=3,
            set_name=self.set_name
        )

        await interaction.followup.send(embed=embed)

        new_achievements = check_achievements(user_id)

        if new_achievements:
            await interaction.followup.send(
                embed=build_new_achievements_embed(
                    interaction.user,
                    new_achievements
                )
            )

    @discord.ui.button(
        label="🔄 Actualiser",
        style=discord.ButtonStyle.secondary
    )
    async def refresh_shop(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user = get_user(interaction.user.id)

        await interaction.response.edit_message(
            embed=build_shop_embed(user, self.set_name),
            view=self
        )