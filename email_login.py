import os

# ──────────────────────────────────────────────────────────────
#  ENVIRONMENT / LOGIN CONFIG
# ──────────────────────────────────────────────────────────────
def load_dotenv(path='.env'):
    root = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(root, path)
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and key not in os.environ:
                os.environ[key] = value

load_dotenv()
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")
GMAIL_USER         = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
NOTIFY_EMAIL       = os.getenv("NOTIFY_EMAIL") or GMAIL_USER
TELEGRAM_TOKEN     = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")
LOOKBACK_DAYS      = int(os.getenv("LOOKBACK_DAYS", "90"))
GEMINI_MODEL       = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def validate_config():
    errors = []
    if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("YOUR_") or GEMINI_API_KEY == "YOUR_GEMINI_KEY":
        errors.append("GEMINI_API_KEY is missing or invalid.")
    if not GMAIL_USER or GMAIL_USER == "you@gmail.com":
        errors.append("GMAIL_USER is missing or invalid.")
    if not GMAIL_APP_PASSWORD or GMAIL_APP_PASSWORD.startswith("YOUR_") or GMAIL_APP_PASSWORD == "YOUR_APP_PASSWORD":
        errors.append("GMAIL_APP_PASSWORD is missing or invalid.")
    if not NOTIFY_EMAIL:
        errors.append("NOTIFY_EMAIL is missing or invalid.")
    if errors:
        raise SystemExit("Configuration error:\n" + "\n".join(f" - {msg}" for msg in errors))
