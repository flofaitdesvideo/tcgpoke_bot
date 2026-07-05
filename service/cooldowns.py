import time

from service.database import get_user, update_user


BOOSTER_COOLDOWN_SECONDS = 10800
# 3600 = 1 heure
# 1800 = 30 minutes
# 86400 = 24 heures


def get_booster_cooldown_remaining(user_id):
    user_id = str(user_id)
    user = get_user(user_id)

    cooldowns = user.get("cooldowns", {})
    booster_available_at = cooldowns.get("booster_available_at", 0)

    now = int(time.time())

    remaining = booster_available_at - now

    if remaining <= 0:
        return 0

    return remaining


def set_booster_cooldown(user_id):
    user_id = str(user_id)
    user = get_user(user_id)

    cooldowns = user.get("cooldowns", {})

    cooldowns["booster_available_at"] = int(time.time()) + BOOSTER_COOLDOWN_SECONDS

    user["cooldowns"] = cooldowns

    update_user(
        user_id,
        user
    )


def format_cooldown(seconds):
    seconds = int(seconds)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}min"

    if minutes > 0:
        return f"{minutes}min {secs}s"

    return f"{secs}s"