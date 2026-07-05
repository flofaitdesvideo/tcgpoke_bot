import random
from datetime import datetime
from typing import Any, Dict, List

from service.database import (
    get_user,
    update_user,
    add_coins,
    add_xp,
)


# ============================================================
# CONFIG MISSIONS
# ============================================================

MISSION_POOL = {
    "open_1_booster": {
        "name": "Petit opening",
        "description": "Ouvre 1 booster.",
        "event": "booster_opened",
        "target": 1,
        "coins": 150,
        "xp": 25,
        "gems": 0,
        "emoji": "🎁",
    },
    "open_3_boosters": {
        "name": "Session boosters",
        "description": "Ouvre 3 boosters.",
        "event": "booster_opened",
        "target": 3,
        "coins": 400,
        "xp": 60,
        "gems": 1,
        "emoji": "📦",
    },
    "collect_20_cards": {
        "name": "Collection rapide",
        "description": "Obtiens 20 cartes.",
        "event": "card_collected",
        "target": 20,
        "coins": 300,
        "xp": 50,
        "gems": 0,
        "emoji": "🃏",
    },
    "sell_5_cards": {
        "name": "Vide-grenier Pokémon",
        "description": "Vends 5 cartes en double.",
        "event": "card_sold",
        "target": 5,
        "coins": 350,
        "xp": 45,
        "gems": 0,
        "emoji": "💰",
    },
    "trade_1_card": {
        "name": "Premier deal du jour",
        "description": "Réalise 1 échange.",
        "event": "trade_completed",
        "target": 1,
        "coins": 500,
        "xp": 70,
        "gems": 1,
        "emoji": "🤝",
    },
}


DAILY_MISSION_COUNT = 3


# ============================================================
# OUTILS
# ============================================================

def today_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_default_missions() -> Dict[str, Any]:
    selected_ids = random.sample(
        list(MISSION_POOL.keys()),
        k=min(DAILY_MISSION_COUNT, len(MISSION_POOL))
    )

    active = {}

    for mission_id in selected_ids:
        active[mission_id] = {
            "progress": 0,
            "claimed": False,
        }

    return {
        "date": today_key(),
        "active": active,
    }


def get_user_missions(user_id: Any) -> Dict[str, Any]:
    user = get_user(user_id)

    missions = user.get("missions")

    if not missions or missions.get("date") != today_key():
        missions = get_default_missions()

        update_user(
            user_id,
            {
                "missions": missions
            }
        )

    return missions


def save_user_missions(
    user_id: Any,
    missions: Dict[str, Any]
):
    update_user(
        user_id,
        {
            "missions": missions
        }
    )


# ============================================================
# PROGRESSION
# ============================================================

def record_mission_progress(
    user_id: Any,
    event: str,
    amount: int = 1
) -> List[Dict[str, Any]]:
    """
    À appeler après une action :
    - booster_opened
    - card_collected
    - card_sold
    - trade_completed
    """

    if amount <= 0:
        return []

    missions = get_user_missions(user_id)
    active = missions.get("active", {})

    updated = []

    for mission_id, state in active.items():
        mission = MISSION_POOL.get(mission_id)

        if not mission:
            continue

        if mission["event"] != event:
            continue

        if state.get("claimed"):
            continue

        target = int(mission["target"])
        current = int(state.get("progress", 0))

        new_progress = min(
            target,
            current + amount
        )

        state["progress"] = new_progress

        updated.append(
            get_mission_status(
                mission_id,
                state
            )
        )

    save_user_missions(
        user_id,
        missions
    )

    return updated


def get_mission_status(
    mission_id: str,
    state: Dict[str, Any]
) -> Dict[str, Any]:

    mission = MISSION_POOL[mission_id]

    progress = int(state.get("progress", 0))
    target = int(mission["target"])
    claimed = bool(state.get("claimed", False))

    return {
        "id": mission_id,
        "name": mission["name"],
        "description": mission["description"],
        "emoji": mission["emoji"],
        "target": target,
        "progress": progress,
        "completed": progress >= target,
        "claimed": claimed,
        "coins": mission["coins"],
        "xp": mission["xp"],
        "gems": mission["gems"],
    }


def get_all_mission_statuses(user_id: Any) -> List[Dict[str, Any]]:
    missions = get_user_missions(user_id)
    active = missions.get("active", {})

    statuses = []

    for mission_id, state in active.items():
        if mission_id not in MISSION_POOL:
            continue

        statuses.append(
            get_mission_status(
                mission_id,
                state
            )
        )

    return statuses


# ============================================================
# RÉCOMPENSES
# ============================================================

def claim_completed_missions(user_id: Any) -> Dict[str, Any]:
    missions = get_user_missions(user_id)
    active = missions.get("active", {})

    claimed_missions = []

    total_coins = 0
    total_xp = 0
    total_gems = 0

    for mission_id, state in active.items():
        if mission_id not in MISSION_POOL:
            continue

        mission = MISSION_POOL[mission_id]

        progress = int(state.get("progress", 0))
        target = int(mission["target"])
        claimed = bool(state.get("claimed", False))

        if claimed:
            continue

        if progress < target:
            continue

        state["claimed"] = True

        total_coins += int(mission["coins"])
        total_xp += int(mission["xp"])
        total_gems += int(mission["gems"])

        claimed_missions.append(
            get_mission_status(
                mission_id,
                state
            )
        )

    if total_coins > 0:
        add_coins(
            user_id,
            total_coins
        )

    if total_xp > 0:
        add_xp(
            user_id,
            total_xp
        )

    if total_gems > 0:
        user = get_user(user_id)
        gems = int(user.get("gems", 0))

        update_user(
            user_id,
            {
                "gems": gems + total_gems
            }
        )

    save_user_missions(
        user_id,
        missions
    )

    return {
        "claimed": claimed_missions,
        "coins": total_coins,
        "xp": total_xp,
        "gems": total_gems,
    }


def reset_daily_missions(user_id: Any):
    missions = get_default_missions()

    update_user(
        user_id,
        {
            "missions": missions
        }
    )

    return missions