import os
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())


def clean_token(value):
    if not value:
        return None

    value = value.strip().replace('"', '').replace("'", "")

    if value.lower().startswith("bot "):
        value = value[4:].strip()

    return value


PREFIX = os.getenv("PREFIX", "!")

DISCORD_TOKEN = clean_token(
    os.getenv("DISCORD_TOKEN")
)

FIREBASE_KEY_PATH = os.getenv(
    "FIREBASE_KEY_PATH",
    "firebase-key.json"
)

WEB_SECRET_KEY = os.getenv(
    "WEB_SECRET_KEY",
    "dev-secret-key"
)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


# ============================================================
# DISCORD OAUTH2 DASHBOARD
# ============================================================

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")

DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")

DISCORD_REDIRECT_URI = os.getenv(
    "DISCORD_REDIRECT_URI",
    "http://127.0.0.1:5000/auth/discord/callback"
)

ADMIN_DISCORD_IDS = [
    item.strip()
    for item in os.getenv("ADMIN_DISCORD_IDS", "").split(",")
    if item.strip()
]

DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

ADMIN_ROLE_IDS = [
    item.strip()
    for item in os.getenv("ADMIN_ROLE_IDS", "").split(",")
    if item.strip()
]


def require_env(name: str, value: str | None):
    if not value:
        raise RuntimeError(
            f"Variable d'environnement manquante : {name}"
        )

    return value