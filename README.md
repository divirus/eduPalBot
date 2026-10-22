# eduPalBot

Telegram tutor for essay writing and mathematics using GigaChat.

## Run

Use Python 3.10 or newer. Install dependencies with `python -m pip install -r requirements.txt`.
Set `TELEGRAM_TOKEN` and `GIGACHAT_AUTH_KEY` in the process environment, then run `python main.py`.
See `.env.example` for variable names; the application does not load `.env` files.
The bundled PEM files contain public CA certificates, not private keys.

An optional standalone Hugging Face implementation is available via `python edu_pal_bot.py`.
It requires `TELEGRAM_TOKEN` and `HF_API_TOKEN`; `HF_API_URL` can override the legacy inference endpoint.
Availability of that provider endpoint depends on the provider.

The current main entry point uses the GigaChat conversations and does not enable the historical
SQLite subscription or analytics integrations. Their modules remain available for reference.
Pandoc is required for LaTeX conversion; handlers fall back to the original text if conversion fails.

## Checks

Run `python -m unittest discover -s tests -v`.

## Credential hygiene

Supply credentials using deployment secrets or environment variables. Keep tokens, local databases,
logs and virtual environments out of Git. Request bodies and provider response bodies must not be logged.

Previously committed credentials must be revoked and replaced with their providers: Telegram BotFather,
GigaChat, Graspil and Yandex OAuth/IAM. Update deployment secrets after rotation. Removing credentials
from Git history does not revoke them. If a Google Analytics property identifier was exposed, review its
configuration as well.

After the history rewrite, existing clones should be replaced with fresh clones. Do not merge or push
old branches back into this repository. Cached commits, forks and external clones may still retain old
objects; contact GitHub Support if sensitive cached views need removal.
