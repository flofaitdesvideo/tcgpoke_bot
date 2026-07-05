import asyncio
from functools import wraps
from urllib.parse import urlencode

import requests

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    redirect,
    session,
    url_for,
    flash,
)

from service.database import (
    get_all_users,
    get_user,
    update_user,
    add_coins,
    remove_coins,
)

from service.missions import reset_daily_missions

from service.inventory import (
    add_card,
    refresh_inventory_rarities,
)

from service.tcg_api import search_card
from service.booster import normalize_rarity_name

from bot.config import (
    WEB_SECRET_KEY,
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    DISCORD_REDIRECT_URI,
    ADMIN_DISCORD_IDS,
    DISCORD_GUILD_ID,
    ADMIN_ROLE_IDS,
)


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)

app.secret_key = WEB_SECRET_KEY


DISCORD_API_BASE_URL = "https://discord.com/api"
DISCORD_AUTH_URL = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"


def login_required(route):
    @wraps(route)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))

        return route(*args, **kwargs)

    return wrapper


@app.route("/login")
def login():
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify guilds.members.read",
        "prompt": "consent",
    }

    discord_login_url = f"{DISCORD_AUTH_URL}?{urlencode(params)}"

    return redirect(discord_login_url)


def user_has_admin_role(access_token):
    if not DISCORD_GUILD_ID:
        return False

    if not ADMIN_ROLE_IDS:
        return False

    member_response = requests.get(
        f"{DISCORD_API_BASE_URL}/users/@me/guilds/{DISCORD_GUILD_ID}/member",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        timeout=10
    )

    if member_response.status_code != 200:
        print(
            "[DISCORD ROLE ERROR]",
            member_response.status_code,
            member_response.text
        )
        return False

    member_data = member_response.json()
    user_role_ids = member_data.get("roles", [])

    for role_id in user_role_ids:
        if str(role_id) in ADMIN_ROLE_IDS:
            return True

    return False


@app.route("/auth/discord/callback")
def discord_callback():
    code = request.args.get("code")

    if not code:
        flash("Connexion Discord annulée.", "error")
        return redirect(url_for("login"))

    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    token_response = requests.post(
        DISCORD_TOKEN_URL,
        data=data,
        headers=headers,
        timeout=10
    )

    if token_response.status_code != 200:
        print(
            "[DISCORD TOKEN ERROR]",
            token_response.status_code,
            token_response.text
        )
        flash("Erreur pendant la connexion Discord.", "error")
        return redirect(url_for("login"))

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        flash("Token Discord invalide.", "error")
        return redirect(url_for("login"))

    user_response = requests.get(
        f"{DISCORD_API_BASE_URL}/users/@me",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        timeout=10
    )

    if user_response.status_code != 200:
        flash("Impossible de récupérer ton profil Discord.", "error")
        return redirect(url_for("login"))

    discord_user = user_response.json()
    discord_id = str(discord_user.get("id"))

    is_allowed_user = discord_id in ADMIN_DISCORD_IDS
    is_allowed_role = user_has_admin_role(access_token)

    if not is_allowed_user and not is_allowed_role:
        session.clear()
        flash("Accès refusé. Tu n'as pas le rôle autorisé.", "error")
        return redirect(url_for("login_denied"))

    session["admin_logged_in"] = True
    session["admin_discord_id"] = discord_id
    session["admin_username"] = discord_user.get("username")
    session["admin_global_name"] = discord_user.get("global_name")
    session["admin_avatar"] = discord_user.get("avatar")

    flash("Connexion Discord réussie.", "success")

    return redirect(url_for("dashboard"))


@app.route("/login-denied")
def login_denied():
    return """
    <div style="max-width:500px;margin:100px auto;font-family:sans-serif;text-align:center;">
        <h1>Accès refusé</h1>
        <p>Ton compte Discord n'a pas le rôle autorisé pour accéder au dashboard.</p>
        <a href="/login">Réessayer</a>
    </div>
    """


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ============================================================
# OUTILS STATS
# ============================================================

def get_total_cards(user):
    inventory = user.get("inventory", [])

    total = 0

    for card in inventory:
        total += int(card.get("count", 1))

    return total


def get_unique_cards(user):
    return len(user.get("inventory", []))


def get_inventory_value(user):
    inventory = user.get("inventory", [])

    total = 0

    for card in inventory:
        value = int(card.get("value", 1))
        count = int(card.get("count", 1))

        total += value * count

    return total


def get_best_card(user):
    inventory = user.get("inventory", [])

    if not inventory:
        return None

    return sorted(
        inventory,
        key=lambda card: int(card.get("value", 0)),
        reverse=True
    )[0]


def prepare_user(user):
    inventory = user.get("inventory", [])
    stats = user.get("stats", {})
    achievements = user.get("achievements", [])

    user_id = str(user.get("id", "unknown"))

    name = (
        user.get("display_name")
        or user.get("username")
        or user.get("name")
        or f"Joueur {user_id}"
    )

    return {
        "id": user_id,
        "name": name,
        "avatar_url": user.get("avatar_url"),
        "coins": user.get("coins", 0),
        "gems": user.get("gems", 0),
        "level": user.get("level", 1),
        "xp": user.get("xp", 0),
        "total_cards": len(inventory),
        "unique_cards": len(set(card.get("id") for card in inventory)),
        "collection_value": sum(card.get("value", 0) for card in inventory),
        "boosters_opened": stats.get("boosters_opened", 0),
        "trades": stats.get("trades", 0),
        "achievements": len(achievements),
        "raw": user
    }


def get_dashboard_stats(users):
    total_players = len(users)
    total_cards = 0
    total_unique_cards = 0
    total_coins = 0
    total_gems = 0
    total_boosters = 0
    total_trades = 0
    total_value = 0

    for user in users:
        prepared = prepare_user(user)

        total_cards += prepared["total_cards"]
        total_unique_cards += prepared["unique_cards"]
        total_coins += prepared["coins"]
        total_gems += prepared["gems"]
        total_boosters += prepared["boosters_opened"]
        total_trades += prepared["trades"]
        total_value += prepared["collection_value"]

    return {
        "players": total_players,
        "cards": total_cards,
        "unique_cards": total_unique_cards,
        "coins": total_coins,
        "gems": total_gems,
        "boosters": total_boosters,
        "trades": total_trades,
        "value": total_value,
    }


def get_user_by_id(user_id):
    users = get_all_users(limit=500)

    for user in users:
        if str(user.get("id")) == str(user_id):
            return user

    return None

def filter_cards_for_web_admin(
    cards,
    extension=None,
    rarete=None
):
    filtered = []

    extension_query = extension.lower().strip() if extension else None
    rarity_query = rarete.lower().strip() if rarete else None

    for card in cards:

        if extension_query:
            set_data = card.get("set", {})
            set_id = str(set_data.get("id", "")).lower()
            set_name = str(set_data.get("name", "")).lower()

            if extension_query not in set_id and extension_query not in set_name:
                continue

        if rarity_query:
            card_rarity = normalize_rarity_name(
                card.get("rarity")
            )

            if card_rarity != rarity_query:
                continue

        filtered.append(card)

    return filtered
# ============================================================
# ROUTES WEB
# ============================================================

@app.route("/")
@login_required
def dashboard():
    users = get_all_users(limit=500)
    prepared_users = [prepare_user(user) for user in users]

    stats = get_dashboard_stats(users)

    top_users = sorted(
        prepared_users,
        key=lambda user: user["collection_value"],
        reverse=True
    )[:5]

    return render_template(
        "dashboard.html",
        stats=stats,
        top_users=top_users
    )


@app.route("/users")
@login_required
def users():
    query = request.args.get("q", "").lower().strip()

    users = get_all_users(limit=500)

    prepared_users = [
        prepare_user(user)
        for user in users
    ]

    if query:
        prepared_users = [
            user for user in prepared_users
            if query in user["id"].lower()
            or query in user.get("name", "").lower()
        ]

    prepared_users = sorted(
        prepared_users,
        key=lambda user: user["collection_value"],
        reverse=True
    )

    return render_template(
        "users.html",
        users=prepared_users,
        query=query
    )
    


@app.route("/users/<user_id>")
@login_required
def user_detail(user_id):
    user = get_user_by_id(user_id)

    if not user:
        return "Joueur introuvable", 404

    prepared = prepare_user(user)
    inventory = user.get("inventory", [])

    inventory = sorted(
        inventory,
        key=lambda card: int(card.get("value", 0)),
        reverse=True
    )

    best_card = get_best_card(user)

    return render_template(
        "user_detail.html",
        user=prepared,
        inventory=inventory,
        best_card=best_card
    )


@app.route("/leaderboard")
@login_required
def leaderboard():
    users = get_all_users(limit=500)

    prepared_users = [
        prepare_user(user)
        for user in users
    ]

    rankings = {
        "value": sorted(
            prepared_users,
            key=lambda user: user["collection_value"],
            reverse=True
        )[:10],
        "coins": sorted(
            prepared_users,
            key=lambda user: user["coins"],
            reverse=True
        )[:10],
        "level": sorted(
            prepared_users,
            key=lambda user: user["level"],
            reverse=True
        )[:10],
        "cards": sorted(
            prepared_users,
            key=lambda user: user["total_cards"],
            reverse=True
        )[:10],
    }

    return render_template(
        "leaderboard.html",
        rankings=rankings
    )


# ============================================================
# API JSON
# ============================================================

@app.route("/api/stats")
def api_stats():
    users = get_all_users(limit=500)
    return jsonify(get_dashboard_stats(users))


@app.route("/api/users")
def api_users():
    users = get_all_users(limit=500)
    prepared_users = [prepare_user(user) for user in users]

    return jsonify(prepared_users)

# ============================================================
# ACTIONS ADMIN WEB
# ============================================================

@app.post("/users/<user_id>/give-coins")
@login_required
def web_give_coins(user_id):
    amount = int(request.form.get("amount", 0))

    if amount <= 0:
        flash("Le montant doit être supérieur à 0.", "error")
        return redirect(url_for("user_detail", user_id=user_id))

    add_coins(user_id, amount)

    flash(f"{amount} PokéCoins ajoutés.", "success")
    return redirect(url_for("user_detail", user_id=user_id))


@app.post("/users/<user_id>/take-coins")
@login_required
def web_take_coins(user_id):
    amount = int(request.form.get("amount", 0))

    if amount <= 0:
        flash("Le montant doit être supérieur à 0.", "error")
        return redirect(url_for("user_detail", user_id=user_id))

    success = remove_coins(user_id, amount)

    if not success:
        flash("Le joueur n'a pas assez de PokéCoins.", "error")
    else:
        flash(f"{amount} PokéCoins retirés.", "success")

    return redirect(url_for("user_detail", user_id=user_id))


@app.post("/users/<user_id>/give-gems")
@login_required
def web_give_gems(user_id):
    amount = int(request.form.get("amount", 0))

    if amount <= 0:
        flash("Le montant doit être supérieur à 0.", "error")
        return redirect(url_for("user_detail", user_id=user_id))

    user = get_user(user_id)
    current_gems = int(user.get("gems", 0))

    update_user(
        user_id,
        {
            "gems": current_gems + amount
        }
    )

    flash(f"{amount} gems ajoutées.", "success")
    return redirect(url_for("user_detail", user_id=user_id))


@app.post("/users/<user_id>/set-level")
@login_required
def web_set_level(user_id):
    level = int(request.form.get("level", 1))
    xp = int(request.form.get("xp", 0))

    if level <= 0:
        flash("Le niveau doit être supérieur à 0.", "error")
        return redirect(url_for("user_detail", user_id=user_id))

    if xp < 0:
        xp = 0

    update_user(
        user_id,
        {
            "level": level,
            "xp": xp
        }
    )

    flash(f"Niveau défini sur {level} avec {xp} XP.", "success")
    return redirect(url_for("user_detail", user_id=user_id))


@app.post("/users/<user_id>/reset-daily")
@login_required
def web_reset_daily(user_id):
    update_user(
        user_id,
        {
            "daily": 0
        }
    )

    flash("Daily réinitialisé.", "success")
    return redirect(url_for("user_detail", user_id=user_id))


@app.post("/users/<user_id>/reset-missions")
@login_required
def web_reset_missions(user_id):
    reset_daily_missions(user_id)

    flash("Missions quotidiennes réinitialisées.", "success")
    return redirect(url_for("user_detail", user_id=user_id))
@app.post("/users/<user_id>/give-card")
@login_required
def web_give_card(user_id):
    nom = request.form.get("nom", "").strip()
    extension = request.form.get("extension", "").strip()
    rarete = request.form.get("rarete", "").strip()
    quantite = int(request.form.get("quantite", 1))

    if not nom:
        flash("Le nom de la carte est obligatoire.", "error")
        return redirect(url_for("user_detail", user_id=user_id))

    if quantite <= 0:
        flash("La quantité doit être supérieure à 0.", "error")
        return redirect(url_for("user_detail", user_id=user_id))

    try:
        results = asyncio.run(
            search_card(
                nom,
                limit=100
            )
        )
    except Exception as e:
        flash(f"Erreur pendant la recherche de carte : {e}", "error")
        return redirect(url_for("user_detail", user_id=user_id))

    if not results:
        flash(f"Aucune carte trouvée pour {nom}.", "error")
        return redirect(url_for("user_detail", user_id=user_id))

    filtered_results = filter_cards_for_web_admin(
        results,
        extension=extension or None,
        rarete=rarete or None
    )

    if not filtered_results:
        flash("Aucune carte ne correspond à ces filtres.", "error")
        return redirect(url_for("user_detail", user_id=user_id))

    selected_card = filtered_results[0]

    for _ in range(quantite):
        add_card(
            user_id,
            selected_card,
            amount=1
        )

    card_name = selected_card.get("name", "Carte inconnue")
    rarity = selected_card.get("rarity", "Rareté inconnue")
    set_name = selected_card.get("set", {}).get("name", "Extension inconnue")
    set_id = selected_card.get("set", {}).get("id", "unknown")

    flash(
        f"Carte ajoutée : {card_name} x{quantite} — {set_name} ({set_id}) — {rarity}",
        "success"
    )

    return redirect(url_for("user_detail", user_id=user_id))

@app.post("/users/<user_id>/refresh-rarities")
@login_required
def web_refresh_rarities(user_id):
    count = refresh_inventory_rarities(
        user_id
    )

    flash(
        f"Raretés recalculées pour {count} carte(s).",
        "success"
    )

    return redirect(url_for("user_detail", user_id=user_id))

@app.route("/favicon.ico")
def favicon():
    return "", 204
# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )