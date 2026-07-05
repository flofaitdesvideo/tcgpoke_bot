import discord

from typing import Optional

from discord import app_commands
from discord.ext import commands

from service.database import (
    get_user,
    update_user,
    add_coins,
    remove_coins,
)




from service.tcg_api import (
    search_card,
    clear_cache,
    warmup_tcg_cache,
)

from service.missions import reset_daily_missions
from service.booster import normalize_rarity_name

from service.inventory import (
    add_card,
    get_inventory_stats,
    refresh_inventory_rarities,
    refresh_all_users_rarities,
)
# ============================================================
# OUTILS ADMIN
# ============================================================

def is_admin(interaction: discord.Interaction) -> bool:
    permissions = interaction.user.guild_permissions
    return permissions.administrator


def build_user_info_embed(
    member: discord.Member,
    user_data,
    inventory_stats
) -> discord.Embed:

    stats = user_data.get("stats", {})

    embed = discord.Embed(
        title=f"🛠️ Infos admin — {member.display_name}",
        color=discord.Color.orange()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="👤 Joueur",
        value=(
            f"ID : `{member.id}`\n"
            f"Mention : {member.mention}"
        ),
        inline=False
    )

    embed.add_field(
        name="💰 Économie",
        value=(
            f"PokéCoins : **{user_data.get('coins', 0)}**\n"
            f"Gems : **{user_data.get('gems', 0)}**"
        ),
        inline=True
    )

    embed.add_field(
        name="⭐ Progression",
        value=(
            f"Niveau : **{user_data.get('level', 1)}**\n"
            f"XP : **{user_data.get('xp', 0)}**"
        ),
        inline=True
    )

    embed.add_field(
        name="📚 Collection",
        value=(
            f"Cartes totales : **{inventory_stats['total_cards']}**\n"
            f"Cartes uniques : **{inventory_stats['unique_cards']}**\n"
            f"Doublons : **{inventory_stats['duplicates']}**\n"
            f"Valeur : **{inventory_stats['value']}**"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Stats",
        value=(
            f"Boosters ouverts : **{stats.get('opened', 0)}**\n"
            f"Échanges : **{stats.get('trades', 0)}**\n"
            f"Coins gagnés : **{stats.get('coins_earned', 0)}**"
        ),
        inline=False
    )

    return embed


async def admin_check(interaction: discord.Interaction) -> bool:
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Tu dois être administrateur pour utiliser cette commande.",
            ephemeral=True
        )
        return False

    return True

def filter_cards_for_admin(
    cards,
    extension: Optional[str] = None,
    rarete: Optional[str] = None
):
    filtered = []

    extension_query = extension.lower().strip() if extension else None
    rarity_query = rarete.lower().strip() if rarete else None

    for card in cards:

        # Filtre extension
        if extension_query:
            set_data = card.get("set", {})
            set_id = str(set_data.get("id", "")).lower()
            set_name = str(set_data.get("name", "")).lower()

            if extension_query not in set_id and extension_query not in set_name:
                continue

        # Filtre rareté
        if rarity_query:
            card_rarity = normalize_rarity_name(
                card.get("rarity")
            )

            if card_rarity != rarity_query:
                continue

        filtered.append(card)

    return filtered


# ============================================================
# COG ADMIN
# ============================================================

class Admin(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # --------------------------------------------------------
    # GIVE COINS
    # --------------------------------------------------------

    @app_commands.command(
        name="admin_give_coins",
        description="Admin — Donne des PokéCoins à un joueur"
    )
    @app_commands.describe(
        joueur="Joueur ciblé",
        montant="Montant à donner"
    )
    async def admin_give_coins(
        self,
        interaction: discord.Interaction,
        joueur: discord.Member,
        montant: int
    ):

        if not await admin_check(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        if montant <= 0:
            return await interaction.followup.send(
                "❌ Le montant doit être supérieur à 0.",
                ephemeral=True
            )

        add_coins(
            joueur.id,
            montant
        )

        await interaction.followup.send(
            f"✅ **{montant} PokéCoins** donnés à {joueur.mention}.",
            ephemeral=True
        )

    # --------------------------------------------------------
    # TAKE COINS
    # --------------------------------------------------------

    @app_commands.command(
        name="admin_take_coins",
        description="Admin — Retire des PokéCoins à un joueur"
    )
    @app_commands.describe(
        joueur="Joueur ciblé",
        montant="Montant à retirer"
    )
    async def admin_take_coins(
        self,
        interaction: discord.Interaction,
        joueur: discord.Member,
        montant: int
    ):

        if not await admin_check(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        if montant <= 0:
            return await interaction.followup.send(
                "❌ Le montant doit être supérieur à 0.",
                ephemeral=True
            )

        success = remove_coins(
            joueur.id,
            montant
        )

        if not success:
            return await interaction.followup.send(
                f"❌ {joueur.mention} n'a pas assez de PokéCoins.",
                ephemeral=True
            )

        await interaction.followup.send(
            f"✅ **{montant} PokéCoins** retirés à {joueur.mention}.",
            ephemeral=True
        )

    # --------------------------------------------------------
    # SET LEVEL
    # --------------------------------------------------------

    @app_commands.command(
        name="admin_set_level",
        description="Admin — Définit le niveau d'un joueur"
    )
    @app_commands.describe(
        joueur="Joueur ciblé",
        niveau="Nouveau niveau",
        xp="XP à définir"
    )
    async def admin_set_level(
        self,
        interaction: discord.Interaction,
        joueur: discord.Member,
        niveau: int,
        xp: Optional[int] = 0
    ):

        if not await admin_check(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        if niveau <= 0:
            return await interaction.followup.send(
                "❌ Le niveau doit être supérieur à 0.",
                ephemeral=True
            )

        if xp is None:
            xp = 0

        if xp < 0:
            xp = 0

        update_user(
            joueur.id,
            {
                "level": niveau,
                "xp": xp
            }
        )

        await interaction.followup.send(
            f"✅ Niveau de {joueur.mention} défini sur **{niveau}** avec **{xp} XP**.",
            ephemeral=True
        )

    # --------------------------------------------------------
    # GIVE GEMS
    # --------------------------------------------------------

    @app_commands.command(
        name="admin_give_gems",
        description="Admin — Donne des gems à un joueur"
    )
    @app_commands.describe(
        joueur="Joueur ciblé",
        montant="Montant de gems à donner"
    )
    async def admin_give_gems(
        self,
        interaction: discord.Interaction,
        joueur: discord.Member,
        montant: int
    ):

        if not await admin_check(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        if montant <= 0:
            return await interaction.followup.send(
                "❌ Le montant doit être supérieur à 0.",
                ephemeral=True
            )

        user = get_user(joueur.id)
        current_gems = int(user.get("gems", 0))

        update_user(
            joueur.id,
            {
                "gems": current_gems + montant
            }
        )

        await interaction.followup.send(
            f"✅ **{montant} gems** donnés à {joueur.mention}.",
            ephemeral=True
        )

    # --------------------------------------------------------
    # GIVE CARD
    # --------------------------------------------------------

        @app_commands.command(
        name="admin_give_card",
        description="Admin — Donne une carte Pokémon à un joueur"
    )
        @app_commands.describe(
        joueur="Joueur ciblé",
        nom="Nom de la carte à chercher",
        extension="Nom ou ID de l'extension",
        rarete="Rareté de la carte",
        quantite="Nombre de copies à donner"
    )
        @app_commands.choices(
        rarete=[
            app_commands.Choice(name="Commune", value="common"),
            app_commands.Choice(name="Peu commune", value="uncommon"),
            app_commands.Choice(name="Rare", value="rare"),
            app_commands.Choice(name="Holo", value="holo"),
            app_commands.Choice(name="Ultra rare", value="ultra"),
            app_commands.Choice(name="Secrète", value="secret"),
        ]
    )
        async def admin_give_card(
        self,
        interaction: discord.Interaction,
        joueur: discord.Member,
        nom: str,
        extension: Optional[str] = None,
        rarete: Optional[str] = None,
        quantite: Optional[int] = 1
    ):

            if not await admin_check(interaction):
                return

        await interaction.response.defer(ephemeral=True)

        if quantite is None:
            quantite = 1

        if quantite <= 0:
            return await interaction.followup.send(
                "❌ La quantité doit être supérieure à 0.",
                ephemeral=True
            )

        results = await search_card(
            nom,
            limit=100
        )

        if not results:
            return await interaction.followup.send(
                f"❌ Aucune carte trouvée pour `{nom}`.",
                ephemeral=True
            )

        filtered_results = filter_cards_for_admin(
            results,
            extension=extension,
            rarete=rarete
        )

        if not filtered_results:
            details = []

            if extension:
                details.append(f"extension `{extension}`")

            if rarete:
                details.append(f"rareté `{rarete}`")

            details_text = " avec " + " et ".join(details) if details else ""

            return await interaction.followup.send(
                f"❌ Aucune carte trouvée pour `{nom}`{details_text}.",
                ephemeral=True
            )

        selected_card = filtered_results[0]

        for _ in range(quantite):
            add_card(
                joueur.id,
                selected_card,
                amount=1
            )

        card_name = selected_card.get(
            "name",
            "Carte inconnue"
        )

        rarity = selected_card.get(
            "rarity",
            "Rareté inconnue"
        )

        set_name = selected_card.get(
            "set",
            {}
        ).get(
            "name",
            "Extension inconnue"
        )

        set_id = selected_card.get(
            "set",
            {}
        ).get(
            "id",
            "unknown"
        )

        await interaction.followup.send(
            (
                f"✅ Carte donnée à {joueur.mention} :\n\n"
                f"🎴 **{card_name}** x{quantite}\n"
                f"📦 Extension : **{set_name}** (`{set_id}`)\n"
                f"⭐ Rareté : **{rarity}**"
            ),
            ephemeral=True
        )

    # --------------------------------------------------------
    # RESET DAILY
    # --------------------------------------------------------

    @app_commands.command(
        name="admin_reset_daily",
        description="Admin — Réinitialise le daily d'un joueur"
    )
    @app_commands.describe(
        joueur="Joueur ciblé"
    )
    async def admin_reset_daily(
        self,
        interaction: discord.Interaction,
        joueur: discord.Member
    ):

        if not await admin_check(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        update_user(
            joueur.id,
            {
                "daily": 0
            }
        )

        await interaction.followup.send(
            f"✅ Daily réinitialisé pour {joueur.mention}.",
            ephemeral=True
        )

    # --------------------------------------------------------
    # RESET MISSIONS
    # --------------------------------------------------------

    @app_commands.command(
        name="admin_reset_missions",
        description="Admin — Réinitialise les missions quotidiennes d'un joueur"
    )
    @app_commands.describe(
        joueur="Joueur ciblé"
    )
    async def admin_reset_missions(
        self,
        interaction: discord.Interaction,
        joueur: discord.Member
    ):

        if not await admin_check(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        reset_daily_missions(
            joueur.id
        )

        await interaction.followup.send(
            f"✅ Missions quotidiennes réinitialisées pour {joueur.mention}.",
            ephemeral=True
        )

    # --------------------------------------------------------
    # RELOAD TCG CACHE
    # --------------------------------------------------------

    @app_commands.command(
        name="admin_reload_tcg",
        description="Admin — Recharge le cache TCGdex"
    )
    async def admin_reload_tcg(
        self,
        interaction: discord.Interaction
    ):

        if not await admin_check(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        clear_cache()

        result = await warmup_tcg_cache()

        await interaction.followup.send(
            (
                "✅ Cache TCGdex rechargé.\n"
                f"Extensions chargées : **{result.get('sets', 0)}**\n"
                f"Sets de cartes en cache : **{result.get('cached_card_sets', 0)}**"
            ),
            ephemeral=True
        )

    # --------------------------------------------------------
    # USER INFO
    # --------------------------------------------------------

    @app_commands.command(
        name="admin_user_info",
        description="Admin — Affiche les infos d'un joueur"
    )
    @app_commands.describe(
        joueur="Joueur ciblé"
    )
    async def admin_user_info(
        self,
        interaction: discord.Interaction,
        joueur: discord.Member
    ):

        if not await admin_check(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        user_data = get_user(
            joueur.id
        )

        inventory_stats = get_inventory_stats(
            joueur.id
        )

        embed = build_user_info_embed(
            joueur,
            user_data,
            inventory_stats
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )
        @app_commands.command(
        name="admin_refresh_rarities",
        description="Admin — Recalcule les raretés d'un joueur"
    )
        @app_commands.describe(
        joueur="Joueur ciblé"
    )
        async def admin_refresh_rarities(
        self,
        interaction: discord.Interaction,
        joueur: discord.Member
    ):

            if not await admin_check(interaction):
                return

        await interaction.response.defer(ephemeral=True)

        count = refresh_inventory_rarities(
            joueur.id
        )

        await interaction.followup.send(
            f"✅ Raretés recalculées pour {joueur.mention} : **{count} carte(s)** corrigée(s).",
            ephemeral=True
        )
        @app_commands.command(
        name="admin_refresh_all_rarities",
        description="Admin — Recalcule les raretés de tous les joueurs"
    )
        async def admin_refresh_all_rarities(
        self,
        interaction: discord.Interaction
    ):

            if not await admin_check(interaction):
                return

        await interaction.response.defer(ephemeral=True)

        result = refresh_all_users_rarities(
            limit=500
        )

        await interaction.followup.send(
            (
                "✅ Raretés recalculées pour tous les joueurs.\n\n"
                f"👥 Joueurs : **{result['users']}**\n"
                f"🃏 Cartes : **{result['cards']}**"
            ),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Admin(bot))