import discord
from discord import app_commands
from discord.ext import commands

from service.shop import SHOP_ITEMS
from service.economy import get_balance, remove_coins
from service.player import add_pack_open


class Buy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="buy")
    async def buy(self, interaction: discord.Interaction, item: str):

        user_id = str(interaction.user.id)

        if item not in SHOP_ITEMS:
            return await interaction.response.send_message("❌ Item invalide", ephemeral=True)

        shop_item = SHOP_ITEMS[item]
        price = shop_item["price"]

        if not remove_coins(user_id, price):
            return await interaction.response.send_message("❌ Pas assez de coins", ephemeral=True)

        # 🎁 reward
        if shop_item["type"] == "booster":
            add_pack_open(user_id)

        embed = discord.Embed(
            title="✅ Achat réussi",
            description=f"Tu as acheté {shop_item['name']}",
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Buy(bot))