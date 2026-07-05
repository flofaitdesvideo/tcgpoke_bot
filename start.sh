#!/usr/bin/env bash

set -e

PORT="${SERVER_PORT:-${PORT:-5000}}"

echo "🚀 Démarrage du bot Discord..."
python -m bot.main &
BOT_PID=$!

echo "🌐 Démarrage du dashboard sur le port ${PORT}..."
python -m gunicorn \
  --workers 1 \
  --threads 4 \
  --timeout 120 \
  --bind 0.0.0.0:${PORT} \
  web.app:app &
WEB_PID=$!

trap "echo 'Arrêt...'; kill $BOT_PID $WEB_PID; exit" SIGINT SIGTERM

wait -n

echo "❌ Un des deux services s'est arrêté."
kill $BOT_PID $WEB_PID
exit 1