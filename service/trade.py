from copy import deepcopy
from typing import Any, Dict, Optional

from service.inventory import (
    search_inventory,
    get_card,
    get_card_count,
    remove_card,
    add_card,
)

from service.database import increment_stat


# ============================================================
# OUTILS TRADE
# ============================================================

def safe_user_id(user_id: Any) -> str:
    return str(user_id)


def format_trade_card(card: Dict[str, Any]) -> str:
    if not card:
        return "Carte inconnue"

    emoji = card.get("rarity_emoji", "🎴")
    name = card.get("name", "Carte inconnue")
    rarity = card.get("rarity", "Inconnue")
    count = card.get("count", 1)

    set_name = card.get("set", {}).get(
        "name",
        "Extension inconnue"
    )

    return (
        f"{emoji} **{name}** x{count}\n"
        f"Rareté : `{rarity}`\n"
        f"Extension : `{set_name}`"
    )


def find_trade_card(
    user_id: Any,
    query: str
) -> Optional[Dict[str, Any]]:
    """
    Cherche une carte dans l'inventaire d'un joueur.
    Fonctionne avec :
    - l'id exact de la carte
    - le nom exact
    - une recherche partielle
    """

    if not query:
        return None

    query = str(query).strip()

    # 1. Recherche directe par ID
    direct_card = get_card(
        user_id,
        query
    )

    if direct_card:
        return direct_card

    # 2. Recherche par nom
    results = search_inventory(
        user_id,
        query=query,
        sort="value"
    )

    if not results:
        return None

    query_lower = query.lower()

    exact_results = [
        card for card in results
        if card.get("name", "").lower() == query_lower
    ]

    if exact_results:
        return exact_results[0]

    return results[0]


def can_trade_card(
    user_id: Any,
    card_id: str
) -> bool:
    return get_card_count(
        user_id,
        card_id
    ) > 0


# ============================================================
# VALIDATION TRADE
# ============================================================

def validate_trade(
    offerer_id: Any,
    target_id: Any,
    offer_card_id: str,
    requested_card_id: str
) -> Dict[str, Any]:

    offerer_id = safe_user_id(offerer_id)
    target_id = safe_user_id(target_id)

    offer_card = get_card(
        offerer_id,
        offer_card_id
    )

    requested_card = get_card(
        target_id,
        requested_card_id
    )

    if not offer_card:
        return {
            "success": False,
            "reason": "❌ Le créateur de l'échange ne possède plus la carte proposée."
        }

    if not requested_card:
        return {
            "success": False,
            "reason": "❌ Le joueur ciblé ne possède plus la carte demandée."
        }

    if get_card_count(offerer_id, offer_card_id) <= 0:
        return {
            "success": False,
            "reason": "❌ La carte proposée n'est plus disponible."
        }

    if get_card_count(target_id, requested_card_id) <= 0:
        return {
            "success": False,
            "reason": "❌ La carte demandée n'est plus disponible."
        }

    return {
        "success": True,
        "offer_card": offer_card,
        "requested_card": requested_card
    }


def complete_trade(
    offerer_id: Any,
    target_id: Any,
    offer_card_id: str,
    requested_card_id: str
) -> Dict[str, Any]:
    """
    Exécute l'échange.
    On revérifie les deux inventaires juste avant le transfert.
    """
    offerer_id = safe_user_id(offerer_id)
    target_id = safe_user_id(target_id)

    validation = validate_trade(
        offerer_id,
        target_id,
        offer_card_id,
        requested_card_id
    )

    if not validation["success"]:
        return validation

    offer_card = deepcopy(validation["offer_card"])
    requested_card = deepcopy(validation["requested_card"])

    # On retire d'abord les cartes.
    removed_offer = remove_card(
        offerer_id,
        offer_card_id,
        amount=1
    )

    removed_requested = remove_card(
        target_id,
        requested_card_id,
        amount=1
    )

    # Sécurité minimale : si un retrait échoue, on rollback ce qu'on peut.
    if not removed_offer or not removed_requested:

        if removed_offer:
            add_card(
                offerer_id,
                offer_card,
                amount=1
            )

        if removed_requested:
            add_card(
                target_id,
                requested_card,
                amount=1
            )

        return {
            "success": False,
            "reason": "❌ L'échange a échoué pendant le transfert. Aucun échange effectué."
        }

    # On donne les cartes à l'autre joueur.
    add_card(
        target_id,
        offer_card,
        amount=1
    )

    add_card(
        offerer_id,
        requested_card,
        amount=1
    )

    increment_stat(
        offerer_id,
        "trades",
        1
    )

    increment_stat(
        target_id,
        "trades",
        1
    )

    return {
        "success": True,
        "offer_card": offer_card,
        "requested_card": requested_card
    }