from service.player import PLAYERS


# =========================
# 🏆 TOP COINS
# =========================
def get_top_coins(limit=10):
    sorted_players = sorted(
        PLAYERS.items(),
        key=lambda x: x[1]["coins"],
        reverse=True
    )

    return sorted_players[:limit]


# =========================
# ⭐ TOP LEVEL
# =========================
def get_top_level(limit=10):
    sorted_players = sorted(
        PLAYERS.items(),
        key=lambda x: x[1]["level"],
        reverse=True
    )

    return sorted_players[:limit]


# =========================
# 🔥 TOP RARE PULLS
# =========================
def get_top_rares(limit=10):
    sorted_players = sorted(
        PLAYERS.items(),
        key=lambda x: x[1]["rare_pulls"],
        reverse=True
    )

    return sorted_players[:limit]