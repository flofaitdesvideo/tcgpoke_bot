from typing import Any, Dict, List

from service.database import (
    get_user,
    update_user,
    add_coins,
)

from service.inventory import (
    get_inventory_stats,
)


# ============================================================
# LISTE DES SUCCÈS
# ============================================================

ACHIEVEMENTS = {
    "first_booster": {
        "name": "Premier booster",
        "description": "Ouvre ton premier booster.",
        "reward": 100,
        "emoji": "🎁",
    },
    "booster_10": {
        "name": "Collectionneur débutant",
        "description": "Ouvre 10 boosters.",
        "reward": 300,
        "emoji": "📦",
    },
    "booster_50": {
        "name": "Chasseur de cartes",
        "description": "Ouvre 50 boosters.",
        "reward": 1000,
        "emoji": "🔥",
    },
    "cards_50": {
        "name": "Petite collection",
        "description": "Possède 50 cartes au total.",
        "reward": 250,
        "emoji": "🃏",
    },
    "cards_200": {
        "name": "Grande collection",
        "description": "Possède 200 cartes au total.",
        "reward": 1000,
        "emoji": "📚",
    },
    "unique_25": {
        "name": "Pokédex en route",
        "description": "Possède 25 cartes uniques.",
        "reward": 300,
        "emoji": "🎴",
    },
    "unique_100": {
        "name": "Maître collectionneur",
        "description": "Possède 100 cartes uniques.",
        "reward": 1500,
        "emoji": "🏆",
    },
    "value_1000": {
        "name": "Collection précieuse",
        "description": "Atteins 1000 de valeur de collection.",
        "reward": 500,
        "emoji": "💎",
    },
    "value_5000": {
        "name": "Trésor Pokémon",
        "description": "Atteins 5000 de valeur de collection.",
        "reward": 2000,
        "emoji": "👑",
    },
    "first_trade": {
        "name": "Premier échange",
        "description": "Réalise ton premier échange.",
        "reward": 300,
        "emoji": "🤝",
    },
    "trade_10": {
        "name": "Marchand Pokémon",
        "description": "Réalise 10 échanges.",
        "reward": 1000,
        "emoji": "🔁",
    },
    "level_5": {
        "name": "Dresseur confirmé",
        "description": "Atteins le niveau 5.",
        "reward": 500,
        "emoji": "⭐",
    },
    "level_10": {
        "name": "Dresseur expert",
        "description": "Atteins le niveau 10.",
        "reward": 1500,
        "emoji": "🌟",
    },
}


# ============================================================
# OUTILS
# ============================================================

def get_unlocked_achievements(user_id: Any) -> List[str]:
    user = get_user(user_id)

    achievements = user.get(
        "achievements",
        []
    )

    return achievements


def has_achievement(
    user_id: Any,
    achievement_id: str
) -> bool:

    return achievement_id in get_unlocked_achievements(user_id)


def unlock_achievement(
    user_id: Any,
    achievement_id: str
) -> bool:
    """
    Débloque un succès et donne la récompense.
    Retourne True si nouveau succès débloqué.
    """
    if achievement_id not in ACHIEVEMENTS:
        return False

    user = get_user(user_id)

    unlocked = user.get(
        "achievements",
        []
    )

    if achievement_id in unlocked:
        return False

    unlocked.append(achievement_id)

    update_user(
        user_id,
        {
            "achievements": unlocked
        }
    )

    reward = ACHIEVEMENTS[achievement_id].get(
        "reward",
        0
    )

    if reward > 0:
        add_coins(
            user_id,
            reward
        )

    return True


def get_achievement_progress(
    user_id: Any
) -> Dict[str, Any]:

    user = get_user(user_id)
    stats = user.get("stats", {})
    inventory_stats = get_inventory_stats(user_id)

    return {
        "boosters": int(stats.get("opened", 0)),
        "trades": int(stats.get("trades", 0)),
        "level": int(user.get("level", 1)),
        "total_cards": int(inventory_stats.get("total_cards", 0)),
        "unique_cards": int(inventory_stats.get("unique_cards", 0)),
        "collection_value": int(inventory_stats.get("value", 0)),
    }


def check_achievements(user_id: Any) -> List[Dict[str, Any]]:
    """
    Vérifie les succès du joueur.
    Retourne la liste des nouveaux succès débloqués.
    """

    progress = get_achievement_progress(user_id)

    conditions = {
        "first_booster": progress["boosters"] >= 1,
        "booster_10": progress["boosters"] >= 10,
        "booster_50": progress["boosters"] >= 50,

        "cards_50": progress["total_cards"] >= 50,
        "cards_200": progress["total_cards"] >= 200,

        "unique_25": progress["unique_cards"] >= 25,
        "unique_100": progress["unique_cards"] >= 100,

        "value_1000": progress["collection_value"] >= 1000,
        "value_5000": progress["collection_value"] >= 5000,

        "first_trade": progress["trades"] >= 1,
        "trade_10": progress["trades"] >= 10,

        "level_5": progress["level"] >= 5,
        "level_10": progress["level"] >= 10,
    }

    newly_unlocked = []

    for achievement_id, is_valid in conditions.items():

        if not is_valid:
            continue

        unlocked = unlock_achievement(
            user_id,
            achievement_id
        )

        if unlocked:
            achievement = ACHIEVEMENTS[achievement_id].copy()
            achievement["id"] = achievement_id
            newly_unlocked.append(achievement)

    return newly_unlocked


def get_all_achievements_status(user_id: Any) -> List[Dict[str, Any]]:
    """
    Retourne tous les succès avec statut débloqué ou non.
    """

    unlocked = get_unlocked_achievements(user_id)
    progress = get_achievement_progress(user_id)

    statuses = []

    for achievement_id, data in ACHIEVEMENTS.items():

        status = data.copy()
        status["id"] = achievement_id
        status["unlocked"] = achievement_id in unlocked
        status["progress"] = progress

        statuses.append(status)

    return statuses


def format_unlocked_achievement(achievement: Dict[str, Any]) -> str:
    return (
        f"{achievement.get('emoji', '🏆')} "
        f"**{achievement.get('name', 'Succès')}**\n"
        f"{achievement.get('description', '')}\n"
        f"Récompense : **{achievement.get('reward', 0)} PokéCoins**"
    )