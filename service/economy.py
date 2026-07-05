from collections import defaultdict
import time

BALANCE = defaultdict(lambda: 500)
DAILY_COOLDOWN = {}


# =========================
# 💰 GET BALANCE
# =========================
def get_balance(user_id: str):
    return BALANCE[user_id]


# =========================
# ➕ ADD COINS
# =========================
def add_coins(user_id: str, amount: int):
    BALANCE[user_id] += amount


# =========================
# ➖ REMOVE COINS
# =========================
def remove_coins(user_id: str, amount: int):
    if BALANCE[user_id] >= amount:
        BALANCE[user_id] -= amount
        return True
    return False


# =========================
# 🎁 DAILY REWARD
# =========================
def claim_daily(user_id: str):
    now = int(time.time())

    if user_id in DAILY_COOLDOWN:
        if now - DAILY_COOLDOWN[user_id] < 86400:
            return False, 0

    reward = 200
    BALANCE[user_id] += reward
    DAILY_COOLDOWN[user_id] = now

    return True, reward