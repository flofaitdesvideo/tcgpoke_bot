import aiohttp
import random
import time
from typing import Any, Dict, List, Optional


BASE_URL = "https://api.tcgdex.net/v2/fr"

# Cache mémoire
_cache_sets: Optional[List[Dict[str, Any]]] = None
_cache_sets_timestamp: float = 0

_cache_set_details: Dict[str, Dict[str, Any]] = {}
_cache_cards_by_set: Dict[str, List[Dict[str, Any]]] = {}
_cache_card_details: Dict[str, Dict[str, Any]] = {}

CACHE_DURATION = 60 * 60  # 1 heure


# ============================================================
# OUTILS API
# ============================================================

async def fetch_json(url: str) -> Optional[Any]:
    """
    Requête GET sécurisée.
    Retourne None en cas d'erreur API, timeout, 404, etc.
    """
    try:
        timeout = aiohttp.ClientTimeout(total=12)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:

                if response.status != 200:
                    print(f"[TCG API ERROR] {response.status} -> {url}")
                    return None

                return await response.json()

    except Exception as e:
        print(f"[TCG API EXCEPTION] {e} -> {url}")
        return None


def is_cache_valid(timestamp: float) -> bool:
    return time.time() - timestamp < CACHE_DURATION


def safe_text(value: Any, fallback: str = "Inconnu") -> str:
    if value is None:
        return fallback

    if isinstance(value, str) and value.strip():
        return value.strip()

    return fallback


# ============================================================
# NORMALISATION DES DONNÉES
# ============================================================

def normalize_set(raw_set: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convertit un set TCGdex en format stable pour ton bot.
    """
    if not isinstance(raw_set, dict):
        return None

    set_id = raw_set.get("id")
    name = raw_set.get("name")

    if not set_id or not name:
        return None

    return {
        "id": str(set_id),
        "name": safe_text(name),
        "logo": raw_set.get("logo"),
        "symbol": raw_set.get("symbol"),
        "card_count": raw_set.get("cardCount", {}),
        "release_date": raw_set.get("releaseDate"),
        "serie": raw_set.get("serie", {}),
    }


def normalize_card(
    raw_card: Dict[str, Any],
    set_id: Optional[str] = None,
    set_name: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Convertit une carte TCGdex en structure stable pour :
    - inventaire
    - booster
    - collection
    - trade
    """
    if not isinstance(raw_card, dict):
        return None

    card_id = raw_card.get("id")
    name = raw_card.get("name")

    if not card_id or not name:
        return None

    raw_set = raw_card.get("set")

    if isinstance(raw_set, dict):
        final_set_id = raw_set.get("id") or set_id or "unknown"
        final_set_name = raw_set.get("name") or set_name or final_set_id
    else:
        final_set_id = set_id or "unknown"
        final_set_name = set_name or final_set_id

    return {
        "id": str(card_id),
        "local_id": raw_card.get("localId"),
        "name": safe_text(name, "Carte inconnue"),
        "image": raw_card.get("image"),
        "rarity": raw_card.get("rarity") or "Common",
        "category": raw_card.get("category"),
        "types": raw_card.get("types", []),
        "set": {
            "id": str(final_set_id),
            "name": safe_text(final_set_name, str(final_set_id))
        },
    }


# ============================================================
# EXTENSIONS
# ============================================================

async def get_sets(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Récupère toutes les extensions disponibles depuis TCGdex.
    Ne vérifie PAS chaque set un par un, sinon Discord expire.
    """
    global _cache_sets
    global _cache_sets_timestamp

    if (
        not force_refresh
        and _cache_sets is not None
        and is_cache_valid(_cache_sets_timestamp)
    ):
        return _cache_sets

    data = await fetch_json(f"{BASE_URL}/sets")

    if not isinstance(data, list):
        _cache_sets = []
        _cache_sets_timestamp = time.time()
        return []

    sets = []

    for raw_set in data:
        normalized = normalize_set(raw_set)

        if normalized:
            sets.append(normalized)

    # Tri alphabétique propre pour le menu
    sets.sort(key=lambda s: s["name"].lower())

    _cache_sets = sets
    _cache_sets_timestamp = time.time()

    return sets


async def get_valid_sets() -> List[Dict[str, Any]]:
    """
    Compatibilité avec ton ancien code.
    Ici on retourne toutes les extensions connues sans faire 200 requêtes.
    """
    return await get_sets()


async def get_set(set_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère le détail complet d'une extension.
    """
    if not set_id:
        return None

    if set_id in _cache_set_details:
        return _cache_set_details[set_id]

    data = await fetch_json(f"{BASE_URL}/sets/{set_id}")

    if not isinstance(data, dict):
        return None

    _cache_set_details[set_id] = data
    return data


async def search_sets(query: str, limit: int = 25) -> List[Dict[str, Any]]:
    """
    Recherche une extension par nom ou id.
    Utile pour une future commande /sets ou /booster_search.
    """
    query = query.lower().strip()
    sets = await get_sets()

    if not query:
        return sets[:limit]

    results = []

    for s in sets:
        if query in s["name"].lower() or query in s["id"].lower():
            results.append(s)

    return results[:limit]


def paginate_sets(
    sets: List[Dict[str, Any]],
    page: int = 0,
    page_size: int = 25
) -> List[Dict[str, Any]]:
    """
    Discord limite les Select menus à 25 options.
    Cette fonction servira pour les pages d'extensions.
    """
    start = page * page_size
    end = start + page_size

    return sets[start:end]


# ============================================================
# CARTES
# ============================================================

async def get_cards_from_set(set_id: str) -> List[Dict[str, Any]]:
    """
    Récupère toutes les cartes d'une extension avec leurs vraies infos :
    - rareté
    - image
    - types
    - catégorie
    """

    if not set_id:
        return []

    if set_id in _cache_cards_by_set:
        return _cache_cards_by_set[set_id]

    set_data = await get_set(set_id)

    if not isinstance(set_data, dict):
        return []

    raw_cards = set_data.get("cards")

    if not isinstance(raw_cards, list):
        return []

    set_name = set_data.get("name", set_id)

    full_cards = []

    for raw_card in raw_cards:
        card_id = raw_card.get("id")

        if not card_id:
            continue

        full_card = await get_card(card_id)

        if full_card:
            if not full_card.get("set") or full_card["set"].get("id") == "unknown":
                full_card["set"] = {
                    "id": set_id,
                    "name": set_name
                }

            full_cards.append(full_card)

    _cache_cards_by_set[set_id] = full_cards

    return full_cards


async def get_card(card_id: str) -> Optional[Dict[str, Any]]:
    """
    Récupère le détail complet d'une carte.
    """

    if not card_id:
        return None

    if card_id in _cache_card_details:
        return _cache_card_details[card_id]

    data = await fetch_json(f"{BASE_URL}/cards/{card_id}")

    if not isinstance(data, dict):
        return None

    card = normalize_card(data)

    if card:
        _cache_card_details[card_id] = card

    return card


async def get_random_card(set_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retourne une carte aléatoire.
    Si set_id est fourni, tire dans cette extension.
    Sinon tire dans une extension aléatoire.
    """
    if not set_id:
        sets = await get_sets()

        if not sets:
            return None

        set_id = random.choice(sets)["id"]

    cards = await get_cards_from_set(set_id)

    if not cards:
        return None

    return random.choice(cards)


async def search_card(name: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Recherche une carte dans les extensions.
    Attention : cette fonction peut être lente au premier appel,
    car elle charge les sets non encore en cache.
    """
    if not name:
        return []

    query = name.lower().strip()
    sets = await get_sets()

    results = []

    for s in sets:
        cards = await get_cards_from_set(s["id"])

        for card in cards:
            card_name = card.get("name", "").lower()

            if query in card_name:
                results.append(card)

                if len(results) >= limit:
                    return results

    return results


# ============================================================
# OUTILS BOOSTER
# ============================================================

def filter_cards_by_rarity(
    cards: List[Dict[str, Any]],
    rarity: str
) -> List[Dict[str, Any]]:
    """
    Filtre des cartes par rareté.
    """
    if not rarity:
        return cards

    rarity = rarity.lower()

    return [
        card for card in cards
        if card.get("rarity", "").lower() == rarity
    ]


def choose_random_cards(
    cards: List[Dict[str, Any]],
    amount: int = 10
) -> List[Dict[str, Any]]:
    """
    Tire un nombre de cartes depuis une liste sans crash.
    """
    if not cards:
        return []

    if len(cards) <= amount:
        return random.sample(cards, len(cards))

    return random.sample(cards, amount)


# ============================================================
# PRÉCHARGEMENT
# ============================================================

async def warmup_tcg_cache() -> Dict[str, int]:
    """
    Précharge uniquement la liste des extensions.
    Ne charge PAS toutes les cartes au démarrage pour éviter de ralentir le bot.
    """
    sets = await get_sets(force_refresh=True)

    return {
        "sets": len(sets),
        "cached_card_sets": len(_cache_cards_by_set)
    }


def clear_cache():
    """
    Vide le cache mémoire.
    Utile pour une commande admin /reload_tcg.
    """
    global _cache_sets
    global _cache_sets_timestamp
    global _cache_set_details
    global _cache_cards_by_set
    global _cache_card_details

    _cache_sets = None
    _cache_sets_timestamp = 0
    _cache_set_details = {}
    _cache_cards_by_set = {}
    _cache_card_details = {}