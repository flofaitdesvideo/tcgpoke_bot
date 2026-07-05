
import asyncio
import discord

from service.card_format import format_card_embed


async def play_booster_animation(interaction, cards):

    # 🎬 message initial
    embed = discord.Embed(
        title="🎁 Ouverture du booster...",
        description="Préparation des cartes...",
        color=discord.Color.gold()
    )

    msg = await interaction.followup.send(embed=embed)

    revealed = []

    for i, card in enumerate(cards, start=1):

        await asyncio.sleep(1.2)

        card_embed_data = format_card_embed(card)

        embed = discord.Embed(
            title=card_embed_data["title"],
            description=card_embed_data["description"],
            color=card_embed_data["color"]
        )

        if card_embed_data["image"]:
            embed.set_image(url=card_embed_data["image"])

        embed.set_footer(text=f"Carte {i}/{len(cards)}")

        await msg.edit(embed=embed)

        revealed.append(card_embed_data)

    # 🎉 FINAL SUMMARY
    await asyncio.sleep(1)

    final = discord.Embed(
        title="🎉 Booster ouvert !",
        description="Toutes les cartes obtenues :",
        color=discord.Color.green()
    )

    for c in revealed:
        final.add_field(
            name=c["title"],
            value=c["description"],
            inline=False
        )

    await msg.edit(embed=final)