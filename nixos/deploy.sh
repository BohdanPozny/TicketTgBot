#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/srv/tickettgbot"
APP_USER="tickettgbot"
REPO_URL="https://github.com/YOUR/TicketTgBot.git"

sudo mkdir -p "$APP_DIR"
sudo chown "$APP_USER:$APP_USER" "$APP_DIR"

if [ -d "$APP_DIR/.git" ]; then
  sudo -u "$APP_USER" git -C "$APP_DIR" pull
else
  sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_DIR"
fi

sudo -u "$APP_USER" bash -c "
  cd $APP_DIR
  python3 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
"

if [ ! -f "$APP_DIR/.env" ]; then
  sudo -u "$APP_USER" cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo "Created .env from template. Edit $APP_DIR/.env before starting the service."
fi

systemctl is-active tickettgbot && systemctl restart tickettgbot || true

echo "Done. Check: journalctl -u tickettgbot -f"
