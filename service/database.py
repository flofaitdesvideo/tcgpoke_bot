import time
import firebase_admin

from firebase_admin import credentials
from firebase_admin import firestore

from bot.config import FIREBASE_KEY_PATH
# ==========================
# FIREBASE INIT
# ==========================

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==========================
# DEFAULT USER
# ==========================

DEFAULT_USER = {
    "coins": 1000,
    "gems": 0,

    "xp": 0,
    "level": 1,

    "inventory": [],

    "boosters": {},

    "favorites": [],

    "missions": {},

    "achievements": [],

    "stats": {
        "opened": 0,
        "cards": 0,
        "trades": 0,
        "coins_earned": 0
    },

    "daily": 0,

    "created_at": int(time.time())
}

# ==========================
# USER
# ==========================

def get_user_ref(user_id):
    return db.collection("users").document(str(user_id))


def create_user(user_id):

    ref = get_user_ref(user_id)

    if not ref.get().exists:
        ref.set(DEFAULT_USER)

    return ref.get().to_dict()


def get_user(user_id):

    ref = get_user_ref(user_id)

    doc = ref.get()

    if not doc.exists:
        return create_user(user_id)

    return doc.to_dict()


def update_user(user_id, data):

    ref = get_user_ref(user_id)

    ref.set(
        data,
        merge=True
    )

# ==========================
# INVENTORY
# ==========================

def get_inventory(user_id):

    return get_user(user_id).get(
        "inventory",
        []
    )


def save_inventory(user_id, inventory):

    update_user(
        user_id,
        {
            "inventory": inventory
        }
    )


def add_card(user_id, card):

    inventory = get_inventory(user_id)

    for c in inventory:

        if c["id"] == card["id"]:

            c["count"] += 1

            save_inventory(
                user_id,
                inventory
            )

            return

    card["count"] = 1

    inventory.append(card)

    save_inventory(
        user_id,
        inventory
    )

    increment_stat(
        user_id,
        "cards"
    )


def remove_card(user_id, card_id):

    inventory = get_inventory(user_id)

    new_inventory = []

    for card in inventory:

        if card["id"] == card_id:

            if card["count"] > 1:

                card["count"] -= 1

                new_inventory.append(card)

        else:

            new_inventory.append(card)

    save_inventory(
        user_id,
        new_inventory
    )

# ==========================
# COINS
# ==========================

def get_coins(user_id):

    return get_user(user_id)["coins"]


def add_coins(user_id, amount):

    user = get_user(user_id)

    user["coins"] += amount

    update_user(
        user_id,
        user
    )

    increment_stat(
        user_id,
        "coins_earned",
        amount
    )


def remove_coins(user_id, amount):

    user = get_user(user_id)

    if user["coins"] < amount:
        return False

    user["coins"] -= amount

    update_user(
        user_id,
        user
    )

    return True

# ==========================
# XP
# ==========================

def add_xp(user_id, xp):

    user = get_user(user_id)

    user["xp"] += xp

    while user["xp"] >= user["level"] * 100:

        user["xp"] -= user["level"] * 100

        user["level"] += 1

    update_user(
        user_id,
        user
    )

# ==========================
# FAVORITES
# ==========================

def toggle_favorite(user_id, card_id):

    user = get_user(user_id)

    fav = user.get(
        "favorites",
        []
    )

    if card_id in fav:

        fav.remove(card_id)

    else:

        fav.append(card_id)

    update_user(
        user_id,
        {
            "favorites": fav
        }
    )

# ==========================
# STATS
# ==========================

def increment_stat(user_id, stat, value=1):

    user = get_user(user_id)

    stats = user.get(
        "stats",
        {}
    )

    stats[stat] = stats.get(
        stat,
        0
    ) + value

    update_user(
        user_id,
        {
            "stats": stats
        }
    )

# ==========================
# LEADERBOARD
# ==========================

def get_all_users(limit=100):
    users = []

    docs = db.collection("users").limit(limit).stream()

    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        users.append(data)

    return users

def update_user_profile(discord_user):
    """
    Sauvegarde le pseudo Discord du joueur dans Firebase.
    """

    user_id = str(discord_user.id)
    user = get_user(user_id)

    avatar_url = None

    if discord_user.avatar:
        avatar_url = discord_user.avatar.url

    user["discord_id"] = user_id
    user["username"] = discord_user.name
    user["display_name"] = discord_user.display_name
    user["avatar_url"] = avatar_url

    update_user(
        user_id,
        user
    )

    return user