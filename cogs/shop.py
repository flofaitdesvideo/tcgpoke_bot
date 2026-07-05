import discord

from typing import Optional

from discord import app_commands
from discord.ext import commands

from service.database import get_user
from service.tcg_api import get_valid_sets
from views.shop_view import ShopView, build_shop_embed
from service.database import update_user_profile

# ============================================================
# AUTOCOMPLETE EXTENSION
# ============================================================

async def build_extension_choices(current: str):
    current = current.lower().strip() if current else ""

    sets = await get_valid_sets()

    results = []

    for extension in sets:
        set_id = str(extension.get("id", ""))
        name = str(extension.get("name", set_id))

        if current:
            if current not in set_id.lower() and current not in name.lower():
                continue

        label = f"{name} ({set_id})"

        results.append(
            app_commands.Choice(
                name=label[:100],
                value=set_id[:100]
            )
        )

        if len(results) >= 25:
            break

    return results


class Shop(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    async def autocomplete_extension(
        self,
        interaction: discord.Interaction,
        current: str
    ):
        return await build_extension_choices(current)

    @app_commands.command(
        name="shop",
        description="Affiche la boutique Pokémon TCG"
    )
    @app_commands.describe(
        extension="Extension à ouvrir dans les boosters"
    )
    @app_commands.autocomplete(
        extension=autocomplete_extension
    )
    async def shop(
        self,
        interaction: discord.Interaction,
        extension: Optional[str] = None
    ):

        await interaction.response.defer()

        user = get_user(interaction.user.id)
        user = await update_user_profile(interaction.user)

        selected_set_id = None
        selected_set_name = "Aléatoire"

        if extension:
            sets = await get_valid_sets()

            for set_data in sets:
                if str(set_data.get("id")) == str(extension):
                    selected_set_id = str(set_data.get("id"))
                    selected_set_name = str(
                        set_data.get("name", selected_set_id)
                    )
                    break

            if not selected_set_id:
                return await interaction.followup.send(
                    "❌ Extension introuvable. Utilise l'autocomplétion de la commande.",
                    ephemeral=True
                )

        view = ShopView(
            interaction.user.id,
            set_id=selected_set_id,
            set_name=selected_set_name
        )

        await interaction.followup.send(
            embed=build_shop_embed(
                user,
                selected_set_name
            ),
            view=view
        )


async def setup(bot):
    await bot.add_cog(Shop(bot))