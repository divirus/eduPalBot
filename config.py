import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY")
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
GIGACHAT_OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
CERT_PATH = str(PROJECT_DIR / "pem" / "russiantrustedca.pem")

# Support the earlier Hugging Face implementation until legacy code is removed.
HF_API_TOKEN = os.getenv("HF_API_TOKEN")
HF_API_URL = os.getenv(
    "HF_API_URL",
    "https://api-inference.huggingface.co/models/ai-forever/rugpt3large_based_on_gpt2",
)


def require_env(*names: str) -> None:
    """Check required environment variables before application startup."""
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Не заданы обязательные переменные окружения: " + ", ".join(missing)
        )

# Configuration retained for optional analytics and subscription modules.
GRASPIL_API_KEY = os.getenv("GRASPIL_API_KEY")
GRASPIL_API_URL = "https://api.graspil.com"
DB_PATH = os.getenv("DB_PATH", "users.db")
