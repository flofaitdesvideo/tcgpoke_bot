from copy import deepcopy
from typing import Any, Dict, List, Optional

from service.database import (
    get_user,
    update_user,
    get_inventory,
    save_inventory,
    increment_stat,
    add_xp,
)

from service.booster import (
    normalize_rarity_name,
    get_rarity_value,
    get_rarity_emoji,
)


# ============================================================
# CONFIG INVENTAIRE
# ============================================================

DEFAULT_PAGE_SIZE = 10


# ============================================================
# OUTILS
# ============================================================

def safe_user_id(user_id: Any) -> str:
    return str(user_id)


def safe_text(value: Any, fallback: str = "Inconnu") -> str:
    if value is None:
        return fallback

    if isinstance(value, str) and value.strip():
        return value.strip()

    return fallback


def get_card_id(card: Dict[str, Any]) -> Optional[str]:
    if not isinstance(card, dict):
        return None

    card_id = card.get("id")

    if not card_id:
        return None

    return str(card_id)


def normalize_set_data(card: Dict[str, Any]) -> Dict[str, str]:
    raw_set = card.get("set")

    if isinstance(raw_set, dict):
        set_id = raw_set.get("id") or "unknown"
        set_name = raw_set.get("name") or set_id

        return {
            "id": str(set_id),
            "name": safe_text(set_name, str(set_id))
        }

    return {
        "id": "unknown",
        "name": "Extension inconnue"
    }


def normalize_card_for_inventory(card: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Nettoie une carte avant de l'enregistrer dans Firebase.
    """
    if not isinstance(card, dict):
        return None

    card_id = get_card_id(card)

    if not card_id:
        return None

    name = safe_text(
        card.get("name"),
        "Carte inconnue"
    )

    rarity = card.get("rarity") or "Common"
    rarity_tier = card.get("rarity_tier") or normalize_rarity_name(rarity)

    return {
        "id": card_id,
        "local_id": card.get("local_id"),
        "name": name,
        "image": card.get("image"),
        "rarity": rarity,
        "rarity_tier": rarity_tier,
        "rarity_emoji": card.get("rarity_emoji") or get_rarity_emoji(rarity),
        "value": card.get("value") or get_rarity_value(rarity),
        "category": card.get("category"),
        "types": card.get("types", []),
        "set": normalize_set_data(card),
        "count": int(card.get("count", 1)),
    }


def find_card_index(
    inventory: List[Dict[str, Any]],
    card_id: str
) -> int:
    for index, card in enumerate(inventory):
        if str(card.get("id")) == str(card_id):
            return index

    return -1


def sort_inventory_cards(
    cards: List[Dict[str, Any]],
    mode: str = "name"
) -> List[Dict[str, Any]]:
    """
    Trie l'inventaire.
    Modes :
    - name
    - rarity
    - value
    - count
    - set
    """
    cards = list(cards)

    if mode == "rarity":
        return sorted(
            cards,
            key=lambda c: c.get("value", 0),
            reverse=True
        )

    if mode == "value":
        return sorted(
            cards,
            key=lambda c: c.get("value", 0),
            reverse=True
        )

    if mode == "count":
        return sorted(
            cards,
            key=lambda c: c.get("count", 0),
            reverse=True
        )

    if mode == "set":
        return sorted(
            cards,
            key=lambda c: c.get("set", {}).get("name", "").lower()
        )

    return sorted(
        cards,
        key=lambda c: c.get("name", "").lower()
    )


# ============================================================
# INVENTAIRE DE BASE
# ============================================================

def get_cards(user_id: Any) -> List[Dict[str, Any]]:
    return get_inventory(
        safe_user_id(user_id)
    )


def save_cards(
    user_id: Any,
    cards: List[Dict[str, Any]]
):
    save_inventory(
        safe_user_id(user_id),
        cards
    )


def get_card(
    user_id: Any,
    card_id: str
) -> Optional[Dict[str, Any]]:
    inventory = get_cards(user_id)

    for card in inventory:
        if str(card.get("id")) == str(card_id):
            return card

    return None


def has_card(
    user_id: Any,
    card_id: str
) -> bool:
    return get_card(user_id, card_id) is not None


def get_card_count(
    user_id: Any,
    card_id: str
) -> int:
    card = get_card(user_id, card_id)

    if not card:
        return 0

    return int(card.get("count", 0))


# ============================================================
# AJOUT / SUPPRESSION
# ============================================================

def add_card(
    user_id: Any,
    card: Dict[str, Any],
    amount: int = 1
) -> Optional[Dict[str, Any]]:
    """
    Ajoute une carte.
    Si elle existe déjà, augmente count.
    """
    if amount <= 0:
        return None

    user_id = safe_user_id(user_id)

    normalized = normalize_card_for_inventory(card)

    if not normalized:
        return None

    inventory = get_cards(user_id)
    card_id = normalized["id"]

    index = find_card_index(
        inventory,
        card_id
    )

    if index >= 0:
        inventory[index]["count"] = int(
            inventory[index].get("count", 1)
        ) + amount

        saved_card = inventory[index]

    else:
        normalized["count"] = amount
        inventory.append(normalized)
        saved_card = normalized

    save_cards(
        user_id,
        inventory
    )

    increment_stat(
        user_id,
        "cards",
        amount
    )

    return saved_card


def add_cards(
    user_id: Any,
    cards: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Ajoute plusieurs cartes en une seule sauvegarde Firebase.
    C'est mieux pour les boosters.
    """
    user_id = safe_user_id(user_id)

    if not cards:
        return []

    inventory = get_cards(user_id)
    added_cards = []

    for raw_card in cards:
        normalized = normalize_card_for_inventory(raw_card)

        if not normalized:
            continue

        card_id = normalized["id"]
        index = find_card_index(
            inventory,
            card_id
        )

        if index >= 0:
            inventory[index]["count"] = int(
                inventory[index].get("count", 1)
            ) + 1

            added_cards.append(
                deepcopy(inventory[index])
            )

        else:
            normalized["count"] = 1
            inventory.append(normalized)

            added_cards.append(
                deepcopy(normalized)
            )

    save_cards(
        user_id,
        inventory
    )

    if added_cards:
        increment_stat(
            user_id,
            "cards",
            len(added_cards)
        )

    return added_cards


def add_booster_cards(
    user_id: Any,
    cards: List[Dict[str, Any]],
    xp_reward: int = 25
) -> List[Dict[str, Any]]:
    """
    Ajoute les cartes d'un booster complet.
    Incrémente aussi les stats booster + XP.
    """
    added = add_cards(
        user_id,
        cards
    )

    if added:
        increment_stat(
            user_id,
            "opened",
            1
        )

        add_xp(
            user_id,
            xp_reward
        )

    return added


def remove_card(
    user_id: Any,
    card_id: str,
    amount: int = 1
) -> bool:
    """
    Retire une ou plusieurs copies d'une carte.
    """
    if amount <= 0:
        return False

    user_id = safe_user_id(user_id)
    inventory = get_cards(user_id)

    index = find_card_index(
        inventory,
        card_id
    )

    if index < 0:
        return False

    current_count = int(
        inventory[index].get("count", 1)
    )

    if current_count > amount:
        inventory[index]["count"] = current_count - amount

    else:
        inventory.pop(index)

    save_cards(
        user_id,
        inventory
    )

    return True


def remove_all_copies(
    user_id: Any,
    card_id: str
) -> bool:
    user_id = safe_user_id(user_id)
    inventory = get_cards(user_id)

    index = find_card_index(
        inventory,
        card_id
    )

    if index < 0:
        return False

    inventory.pop(index)

    save_cards(
        user_id,
        inventory
    )

    return True


# ============================================================
# FAVORIS
# ============================================================

def get_favorites(user_id: Any) -> List[str]:
    user = get_user(
        safe_user_id(user_id)
    )

    return user.get(
        "favorites",
        []
    )


def is_favorite(
    user_id: Any,
    card_id: str
) -> bool:
    return str(card_id) in get_favorites(user_id)


def set_favorite(
    user_id: Any,
    card_id: str,
    value: bool = True
) -> bool:
    user_id = safe_user_id(user_id)

    user = get_user(user_id)
    favorites = user.get("favorites", [])

    card_id = str(card_id)

    if value:
        if card_id not in favorites:
            favorites.append(card_id)
    else:
        if card_id in favorites:
            favorites.remove(card_id)

    update_user(
        user_id,
        {
            "favorites": favorites
        }
    )

    return value


def toggle_favorite(
    user_id: Any,
    card_id: str
) -> bool:
    currently_favorite = is_favorite(
        user_id,
        card_id
    )

    return set_favorite(
        user_id,
        card_id,
        not currently_favorite
    )


def get_favorite_cards(user_id: Any) -> List[Dict[str, Any]]:
    favorites = get_favorites(user_id)
    inventory = get_cards(user_id)

    return [
        card for card in inventory
        if str(card.get("id")) in favorites
    ]


# ============================================================
# RECHERCHE / FILTRES
# ============================================================

def search_inventory(
    user_id: Any,
    query: str = "",
    rarity: Optional[str] = None,
    set_id: Optional[str] = None,
    favorites_only: bool = False,
    sort: str = "name"
) -> List[Dict[str, Any]]:
    inventory = get_cards(user_id)
    favorites = get_favorites(user_id)

    query = query.lower().strip() if query else ""
    rarity = rarity.lower().strip() if rarity else None
    set_id = str(set_id).lower().strip() if set_id else None

    results = []

    for card in inventory:
        card_name = card.get("name", "").lower()
        card_rarity = card.get("rarity_tier") or normalize_rarity_name(
            card.get("rarity")
        )
        card_set_id = card.get("set", {}).get("id", "").lower()
        card_id = str(card.get("id"))

        if query and query not in card_name:
            continue

        if rarity and rarity != card_rarity:
            continue

        if set_id and set_id != card_set_id:
            continue

        if favorites_only and card_id not in favorites:
            continue

        results.append(card)

    return sort_inventory_cards(
        results,
        mode=sort
    )


def get_cards_by_set(
    user_id: Any,
    set_id: str
) -> List[Dict[str, Any]]:
    return search_inventory(
        user_id,
        set_id=set_id
    )


def get_cards_by_rarity(
    user_id: Any,
    rarity: str
) -> List[Dict[str, Any]]:
    return search_inventory(
        user_id,
        rarity=rarity
    )


def get_duplicates(user_id: Any) -> List[Dict[str, Any]]:
    inventory = get_cards(user_id)

    return [
        card for card in inventory
        if int(card.get("count", 1)) > 1
    ]


# ============================================================
# PAGINATION
# ============================================================

def paginate_cards(
    cards: List[Dict[str, Any]],
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE
) -> Dict[str, Any]:
    if page < 0:
        page = 0

    total = len(cards)

    max_page = max(
        0,
        (total - 1) // page_size
    ) if total else 0

    if page > max_page:
        page = max_page

    start = page * page_size
    end = start + page_size

    return {
        "cards": cards[start:end],
        "page": page,
        "page_size": page_size,
        "max_page": max_page,
        "total": total,
        "has_previous": page > 0,
        "has_next": page < max_page,
    }


def get_inventory_page(
    user_id: Any,
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
    query: str = "",
    rarity: Optional[str] = None,
    set_id: Optional[str] = None,
    favorites_only: bool = False,
    sort: str = "name"
) -> Dict[str, Any]:
    cards = search_inventory(
        user_id,
        query=query,
        rarity=rarity,
        set_id=set_id,
        favorites_only=favorites_only,
        sort=sort
    )

    return paginate_cards(
        cards,
        page=page,
        page_size=page_size
    )


# ============================================================
# STATISTIQUES
# ============================================================

def get_total_cards(user_id: Any) -> int:
    inventory = get_cards(user_id)

    return sum(
        int(card.get("count", 1))
        for card in inventory
    )


def get_unique_cards(user_id: Any) -> int:
    return len(
        get_cards(user_id)
    )


def get_inventory_value(user_id: Any) -> int:
    inventory = get_cards(user_id)

    total = 0

    for card in inventory:
        value = int(
            card.get("value", 1)
        )

        count = int(
            card.get("count", 1)
        )

        total += value * count

    return total


def get_best_cards(
    user_id: Any,
    limit: int = 10
) -> List[Dict[str, Any]]:
    inventory = get_cards(user_id)

    sorted_cards = sorted(
        inventory,
        key=lambda c: c.get("value", 0),
        reverse=True
    )

    return sorted_cards[:limit]


def get_inventory_stats(user_id: Any) -> Dict[str, Any]:
    inventory = get_cards(user_id)

    stats = {
        "total_cards": 0,
        "unique_cards": len(inventory),
        "favorites": len(get_favorites(user_id)),
        "duplicates": 0,
        "value": 0,
        "rarities": {
            "common": 0,
            "uncommon": 0,
            "rare": 0,
            "holo": 0,
            "ultra": 0,
            "secret": 0,
        },
        "sets": {},
        "best_card": None,
    }

    best_card = None
    best_value = -1

    for card in inventory:
        count = int(
            card.get("count", 1)
        )

        value = int(
            card.get("value", 1)
        )

        tier = card.get("rarity_tier") or normalize_rarity_name(
            card.get("rarity")
        )

        set_name = card.get("set", {}).get(
            "name",
            "Extension inconnue"
        )

        stats["total_cards"] += count
        stats["value"] += value * count

        if count > 1:
            stats["duplicates"] += count - 1

        if tier not in stats["rarities"]:
            tier = "common"

        stats["rarities"][tier] += count

        if set_name not in stats["sets"]:
            stats["sets"][set_name] = 0

        stats["sets"][set_name] += count

        if value > best_value:
            best_value = value
            best_card = card

    stats["best_card"] = best_card

    return stats


# ============================================================
# FORMAT DISCORD
# ============================================================

def format_inventory_card_line(card: Dict[str, Any]) -> str:
    emoji = card.get("rarity_emoji") or get_rarity_emoji(
        card.get("rarity")
    )

    name = card.get(
        "name",
        "Carte inconnue"
    )

    rarity = card.get(
        "rarity",
        "Common"
    )

    count = int(
        card.get("count", 1)
    )

    set_name = card.get("set", {}).get(
        "name",
        "Extension inconnue"
    )

    return f"{emoji} **{name}** x{count} — {rarity} · {set_name}"


def format_inventory_page(page_data: Dict[str, Any]) -> str:
    cards = page_data.get(
        "cards",
        []
    )

    if not cards:
        return "📭 Aucune carte trouvée."

    lines = []

    for card in cards:
        lines.append(
            format_inventory_card_line(card)
        )

    footer = (
        f"\n\n📄 Page {page_data['page'] + 1}/"
        f"{page_data['max_page'] + 1}"
        f" · {page_data['total']} carte(s)"
    )

    return "\n".join(lines) + footer
# ============================================================
# MAINTENANCE / MIGRATION
# ============================================================

def refresh_inventory_rarities(user_id):
    """
    Recalcule les raretés, emojis et valeurs des cartes d'un joueur.
    Utile après correction de normalize_rarity_name().
    """

    inventory = get_cards(user_id)

    for card in inventory:
        rarity = card.get("rarity", "Common")

        card["rarity_tier"] = normalize_rarity_name(rarity)
        card["rarity_emoji"] = get_rarity_emoji(rarity)
        card["value"] = get_rarity_value(rarity)

    save_cards(
        user_id,
        inventory
    )

    return len(inventory)


def refresh_all_users_rarities(limit=500):
    """
    Recalcule les raretés de tous les joueurs.
    """

    from service.database import get_all_users

    users = get_all_users(limit=limit)

    updated_users = 0
    updated_cards = 0

    for user in users:
        user_id = user.get("id")

        if not user_id:
            continue

        count = refresh_inventory_rarities(user_id)

        updated_users += 1
        updated_cards += count

    return {
        "users": updated_users,
        "cards": updated_cards
    }