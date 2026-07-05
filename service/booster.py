import random
from typing import Any, Dict, List, Optional

from service.tcg_api import get_cards_from_set, get_sets


# ============================================================
# CONFIG BOOSTER
# ============================================================

DEFAULT_BOOSTER_SIZE = 10

# Chances simplifiées mais efficaces pour un bot Discord.
# On ne force pas une rareté inexistante dans une extension.
RARITY_WEIGHTS = {
    "common": 55,
    "uncommon": 25,
    "rare": 12,
    "holo": 5,
    "ultra": 2,
    "secret": 1,
}


# ============================================================
# RARETÉS
# ============================================================

import unicodedata


def normalize_text(value: str) -> str:
    """
    Nettoie un texte :
    - minuscules
    - accents retirés
    - espaces propres
    """
    if not value:
        return ""

    value = str(value).lower().strip()

    value = unicodedata.normalize("NFD", value)
    value = "".join(
        char for char in value
        if unicodedata.category(char) != "Mn"
    )

    return value


def normalize_rarity_name(rarity) -> str:
    """
    Convertit les raretés TCGdex FR/EN en catégories simples :
    common, uncommon, rare, holo, ultra, secret
    """

    value = normalize_text(rarity)

    if not value:
        return "common"

    # Très important : on teste les raretés les plus spécifiques d'abord.

    # Secrètes / gold / rainbow / hyper
    if any(word in value for word in [
        "secret",
        "secrete",
        "hyper",
        "rainbow",
        "gold",
        "or",
        "rare secrete",
        "secret rare",
        "hyper rare",
    ]):
        return "secret"

    # Illustration spéciale
    if any(word in value for word in [
        "special illustration",
        "illustration speciale",
        "rare illustration speciale",
        "special illustration rare",
    ]):
        return "secret"

    # Ultra / V / VMAX / VSTAR / EX / GX / Full Art / Illustration
    if any(word in value for word in [
        "ultra",
        "full art",
        "illustration",
        "double rare",
        "rare double",
        "amazing",
        "magnifique",
        "vmax",
        "vstar",
        "v-union",
        "v union",
        "gx",
        " ex",
        "ex ",
        " ex ",
    ]):
        return "ultra"

    # Holo
    if any(word in value for word in [
        "holo",
        "holographic",
        "holographique",
        "rare holo",
        "holo rare",
        "rare holographique",
    ]):
        return "holo"

    # Peu commune / uncommon
    # À mettre AVANT commune, sinon "Peu Commune" devient "Commune".
    if any(word in value for word in [
        "uncommon",
        "peu commune",
        "peu-commune",
        "peu_commun",
        "peu commun",
    ]):
        return "uncommon"

    # Commune / common
    if any(word in value for word in [
        "common",
        "commune",
        "commun",
    ]):
        return "common"

    # Rare classique
    if "rare" in value:
        return "rare"

    return "common"

def get_rarity_emoji(rarity) -> str:
    tier = normalize_rarity_name(rarity)

    emojis = {
        "common": "⚪",
        "uncommon": "🟢",
        "rare": "🔵",
        "holo": "✨",
        "ultra": "🌈",
        "secret": "👑",
    }

    return emojis.get(tier, "⚪")


def get_rarity_value(rarity: Optional[str]) -> int:
    """
    Valeur approximative d'une carte.
    Servira plus tard pour économie, score, leaderboard.
    """
    tier = normalize_rarity_name(rarity)

    values = {
        "common": 1,
        "uncommon": 3,
        "rare": 8,
        "holo": 15,
        "ultra": 40,
        "secret": 100,
    }

    return values.get(tier, 1)


def is_rare_card(card: Dict[str, Any]) -> bool:
    tier = normalize_rarity_name(card.get("rarity"))
    return tier in ["holo", "ultra", "secret"]


def is_secret_card(card: Dict[str, Any]) -> bool:
    tier = normalize_rarity_name(card.get("rarity"))
    return tier == "secret"


# ============================================================
# ORGANISATION DES CARTES
# ============================================================

def group_cards_by_rarity(cards: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped = {
        "common": [],
        "uncommon": [],
        "rare": [],
        "holo": [],
        "ultra": [],
        "secret": [],
    }

    for card in cards:
        tier = normalize_rarity_name(card.get("rarity"))

        if tier not in grouped:
            tier = "common"

        grouped[tier].append(card)

    return grouped


def get_available_rarities(grouped_cards: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    return [
        rarity for rarity, cards in grouped_cards.items()
        if len(cards) > 0
    ]


def choose_rarity(available_rarities: List[str]) -> str:
    """
    Choisit une rareté selon les poids.
    Si une rareté n'existe pas dans l'extension, elle est ignorée.
    """
    if not available_rarities:
        return "common"

    weights = []

    for rarity in available_rarities:
        weights.append(RARITY_WEIGHTS.get(rarity, 1))

    return random.choices(
        available_rarities,
        weights=weights,
        k=1
    )[0]


def pick_card_from_group(
    grouped_cards: Dict[str, List[Dict[str, Any]]],
    rarity: str
) -> Optional[Dict[str, Any]]:
    cards = grouped_cards.get(rarity, [])

    if not cards:
        return None

    return random.choice(cards)


def clean_card_for_inventory(card: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prépare une carte pour Firebase.
    On évite de stocker trop de données inutiles.
    """
    return {
        "id": card.get("id"),
        "local_id": card.get("local_id"),
        "name": card.get("name", "Carte inconnue"),
        "image": card.get("image"),
        "rarity": card.get("rarity", "Common"),
        "rarity_tier": normalize_rarity_name(card.get("rarity")),
        "rarity_emoji": get_rarity_emoji(card.get("rarity")),
        "value": get_rarity_value(card.get("rarity")),
        "category": card.get("category"),
        "types": card.get("types", []),
        "set": card.get("set", {
            "id": "unknown",
            "name": "Extension inconnue"
        }),
    }


# ============================================================
# OUVERTURE BOOSTER
# ============================================================

async def open_booster(
    set_id: str,
    size: int = DEFAULT_BOOSTER_SIZE
) -> List[Dict[str, Any]]:
    """
    Ouvre un booster dans une extension précise.
    Retourne une liste de cartes prêtes pour l'inventaire.
    """
    if not set_id:
        return []

    cards = await get_cards_from_set(set_id)

    if not cards:
        return []

    clean_cards = [
        card for card in cards
        if isinstance(card, dict) and card.get("id") and card.get("name")
    ]

    if not clean_cards:
        return []

    grouped = group_cards_by_rarity(clean_cards)
    available_rarities = get_available_rarities(grouped)

    booster_cards = []

    for _ in range(size):
        rarity = choose_rarity(available_rarities)
        card = pick_card_from_group(grouped, rarity)

        # Si la rareté choisie n'a finalement pas de carte,
        # on prend une carte aléatoire de secours.
        if not card:
            card = random.choice(clean_cards)

        booster_cards.append(
            clean_card_for_inventory(card)
        )

    return booster_cards


async def open_random_booster(
    size: int = DEFAULT_BOOSTER_SIZE
) -> List[Dict[str, Any]]:
    """
    Ouvre un booster dans une extension aléatoire.
    """
    sets = await get_sets()

    if not sets:
        return []

    selected_set = random.choice(sets)

    return await open_booster(
        selected_set["id"],
        size=size
    )


# ============================================================
# RÉSUMÉ BOOSTER
# ============================================================

def get_booster_summary(cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Génère un résumé utile pour l'affichage Discord.
    """
    summary = {
        "total": len(cards),
        "common": 0,
        "uncommon": 0,
        "rare": 0,
        "holo": 0,
        "ultra": 0,
        "secret": 0,
        "value": 0,
        "best_card": None,
    }

    best_card = None
    best_value = -1

    for card in cards:
        tier = normalize_rarity_name(card.get("rarity"))
        value = get_rarity_value(card.get("rarity"))

        if tier not in summary:
            tier = "common"

        summary[tier] += 1
        summary["value"] += value

        if value > best_value:
            best_value = value
            best_card = card

    summary["best_card"] = best_card

    return summary


def format_card_line(card: Dict[str, Any]) -> str:
    """
    Format court pour afficher une carte dans Discord.
    """
    emoji = card.get("rarity_emoji") or get_rarity_emoji(card.get("rarity"))
    name = card.get("name", "Carte inconnue")
    rarity = card.get("rarity", "Common")
    set_name = card.get("set", {}).get("name", "Extension inconnue")

    return f"{emoji} **{name}** — {rarity} · {set_name}"


def format_booster_result(cards: List[Dict[str, Any]]) -> str:
    """
    Génère un texte complet pour un booster.
    """
    if not cards:
        return "❌ Booster vide."

    lines = []

    for card in cards:
        lines.append(format_card_line(card))

    return "\n".join(lines)


# ============================================================
# COMPATIBILITÉ ANCIEN CODE
# ============================================================

async def generate_booster(set_id: str, size: int = DEFAULT_BOOSTER_SIZE):
    """
    Ancien alias possible.
    """
    return await open_booster(set_id, size)


async def get_booster(set_id: str, size: int = DEFAULT_BOOSTER_SIZE):
    """
    Ancien alias possible.
    """
    return await open_booster(set_id, size)