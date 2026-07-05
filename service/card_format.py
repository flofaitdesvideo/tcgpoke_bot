RARITY_STYLES = {
    "Common": ("⚪", 0xAAAAAA),
    "Uncommon": ("🟢", 0x2ecc71),
    "Rare": ("🔵", 0x3498db),
    "Ultra Rare": ("🟣", 0x9b59b6),
    "Secret Rare": ("🟡", 0xf1c40f),
}


def format_card_embed(card):
    name = card.get("name", "Unknown")
    rarity = card.get("rarity", "Common")

    emoji, color = RARITY_STYLES.get(rarity, ("⚪", 0xAAAAAA))

    image = None
    if card.get("image"):
        image = card["image"]

    embed = {
        "title": f"{emoji} {name}",
        "description": f"**Rareté:** {rarity}",
        "color": color,
        "image": image
    }

    return embed