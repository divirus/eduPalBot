import os
from dotenv import load_dotenv
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# GigaChat
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY")
GIGACHAT_API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
GIGACHAT_OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

# YandexGPT
YANDEX_OAUTH_TOKEN = os.getenv("YANDEX_OAUTH_TOKEN")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_IAM_TOKEN = os.getenv("YANDEX_IAM_TOKEN")
YANDEX_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
YANDEX_IAM_URL = "https://iam.api.cloud.yandex.net/iam/v1/tokens"

# Model switcher (gigachat | yandexgpt)
ACTIVE_AI_MODEL = os.getenv("ACTIVE_AI_MODEL", "yandexgpt")  # Default model

CERT_PATH = "pem/russiantrustedca.pem"  # Путь к сертификату НУЦ Минцифры
# GRASPIL_API_KEY = os.getenv("GRASPIL_API_KEY")
# GRASPIL_API_URL = "https://api.graspil.com"  # Эндпоинт для отправки событий