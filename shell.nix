{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "tickettgbot-dev";

  buildInputs = with pkgs; [
    # Python
    python312
    python312Packages.pip
    python312Packages.virtualenv

    # MySQL client (для підключення до БД)
    mysql80
    libmysqlclient

    # Build tools (потрібні для деяких Python пакетів)
    gcc
    gnumake
    pkg-config

    # Корисні утиліти
    git
    curl
    jq
  ];

  shellHook = ''
    echo "🎟️  TicketTgBot dev environment"
    echo ""

    # Створити venv якщо не існує
    if [ ! -d ".venv" ]; then
      echo "Creating virtual environment..."
      python -m venv .venv
    fi

    # Активувати venv
    source .venv/bin/activate

    # Встановити залежності якщо потрібно
    if [ ! -f ".venv/.installed" ] || [ requirements.txt -nt .venv/.installed ]; then
      echo "Installing dependencies..."
      pip install -r requirements.txt
      touch .venv/.installed
    fi

    # Перевірити наявність .env
    if [ ! -f ".env" ]; then
      echo "⚠️  .env not found. Copying from .env.example..."
      cp .env.example .env
      echo "✏️  Please edit .env and set your BOT_TOKEN and DATABASE_URL"
    fi

    echo "Python: $(python --version)"
    echo "Pip:    $(pip --version)"
    echo ""
    echo "Commands:"
    echo "  uvicorn main:app --reload   - run FastAPI server"
    echo "  python -m bot               - run bot in polling mode"
    echo ""
  '';

  # Потрібно для mysqlclient / aiomysql
  LD_LIBRARY_PATH = "${pkgs.libmysqlclient}/lib";
}
