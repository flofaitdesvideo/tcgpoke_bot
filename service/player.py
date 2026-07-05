from collections import defaultdict

PLAYERS = defaultdict(lambda: {
    "coins": 500,
    "xp": 0,
    "level": 1,
    "opened_packs": 0,
    "rare_pulls": 0,
})


# =========================
# 👤 GET PLAYER
# =========================
def get_player(user_id: str):
    return PLAYERS[user_id]


# =========================
# 💰 ADD COINS
# =========================
def add_coins(user_id: str, amount: int):
    PLAYERS[user_id]["coins"] += amount


# =========================
# 💸 REMOVE COINS
# =========================
def remove_coins(user_id: str, amount: int):
    PLAYERS[user_id]["coins"] = max(0, PLAYERS[user_id]["coins"] - amount)


# =========================
# 📈 ADD XP + LEVEL SYSTEM
# =========================
def add_xp(user_id: str, xp: int):
    p = PLAYERS[user_id]
    p["xp"] += xp

    # level curve simple
    needed = p["level"] * 100

    if p["xp"] >= needed:
        p["xp"] -= needed
        p["level"] += 1
        return True  # level up

    return False


# =========================
# 📦 STATS BOOSTER
# =========================
def add_pack_open(user_id: str):
    PLAYERS[user_id]["opened_packs"] += 1


def add_rare_pull(user_id: str):
    PLAYERS[user_id]["rare_pulls"] += 1