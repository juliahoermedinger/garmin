import os

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Generate one with:\n"
        "  python -c \"import secrets; print(secrets.token_urlsafe(32))\"\n"
        "and put it in a .env file (see .env.example)."
    )

GARMIN_TOKEN_ENC_KEY = os.environ.get("GARMIN_TOKEN_ENC_KEY")
if not GARMIN_TOKEN_ENC_KEY:
    raise RuntimeError(
        "GARMIN_TOKEN_ENC_KEY is not set. Generate one with:\n"
        "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
        "and put it in a .env file (see .env.example)."
    )

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./running_tracker.db")

SYNC_INTERVAL_MINUTES = int(os.environ.get("SYNC_INTERVAL_MINUTES", "30"))

SESSION_COOKIE_NAME = "session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days

# Mark the session cookie Secure (HTTPS-only) in production. Leave false for local
# http://127.0.0.1 dev, set true once deployed behind real HTTPS (e.g. on Render).
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "false").lower() == "true"

# Web Push (browser/phone notifications when new runs sync in). Optional: if any of
# these are unset, the app runs fine but the notification feature stays hidden.
# Generate a keypair with: python -m app.generate_vapid_keys
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY") or None
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY") or None
VAPID_CONTACT_EMAIL = os.environ.get("VAPID_CONTACT_EMAIL") or None
PUSH_ENABLED = bool(VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY and VAPID_CONTACT_EMAIL)
