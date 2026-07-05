import discord


def build_new_achievements_embed(user, new_achievements) -> discord.Embed:
    """
    Affiche les succès nouvellement débloqués.
    user peut être un discord.User / discord.Member ou juste un user_id.
    """

    if hasattr(user, "mention"):
        mention = user.mention
        display_name = getattr(user, "display_name", "Joueur")
        avatar_url = getattr(user.display_avatar, "url", None)
    else:
        mention = f"<@{user}>"
        display_name = "Joueur"
        avatar_url = None

    embed = discord.Embed(
        title="🎉 Nouveaux succès débloqués !",
        description=f"{mention}, tu as débloqué de nouveaux succès.",
        color=discord.Color.green()
    )

    total_reward = 0
    lines = []

    for achievement in new_achievements:
        emoji = achievement.get("emoji", "🏆")
        name = achievement.get("name", "Succès")
        description = achievement.get("description", "")
        reward = int(achievement.get("reward", 0))

        total_reward += reward

        lines.append(
            f"{emoji} **{name}**\n"
            f"{description}\n"
            f"🎁 +**{reward} PokéCoins**"
        )

    embed.add_field(
        name="Succès",
        value="\n\n".join(lines),
        inline=False
    )

    embed.add_field(
        name="Récompense totale",
        value=f"🪙 **{total_reward} PokéCoins**",
        inline=False
    )

    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    embed.set_footer(
        text=f"Bravo {display_name} !"
    )

    return embed