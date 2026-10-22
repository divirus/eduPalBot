# eduPalBot

**A Telegram study assistant for school students and their parents.** The bot helps explain math problems, draft essays, and review literary works. GigaChat generates responses in Russian.

## Why this project exists

Studying independently often calls for a simple explanation: where to start, why an answer is correct, or how to develop an essay topic. Parents may also need support explaining school material in language their child can understand.

eduPalBot brings that support into a familiar chat. Users choose a subject, send a topic or problem, and receive an answer without installing a separate application. For mathematics, the bot requests a detailed explanation of the solution; for literature, it helps draft texts and explore literary works.

The project supports independent learning. Generated solutions and literary facts should be checked, as language models can make mistakes.

## Current features

| Feature | What users can do |
| --- | --- |
| Topic-based essays | Submit a topic and receive a sample essay in Russian |
| Literary summaries | Provide an author and title to receive a text summarizing the work |
| Mathematics | Submit an equation or problem and receive a solution with an explanation of the steps |
| Navigation | Start a new request, switch subjects, or return to the main menu using Telegram buttons |

For example, users can request an essay on “Why helping others matters,” review the plot of *The Captain’s Daughter*, or ask for an explanation of the equation `2x + 3 = 7`.

### Commands

- `/start` — open the main menu.
- `/essay` — open essays and literary summaries.
- `/math` — open mathematics.
- `/cancel` — end the current interaction and return to the menu.
- `/clear` — clear the current conversation data held in the bot’s memory.

## How it works

The main entry point, `main.py`, runs the Telegram bot using polling. Handlers in `gigachat/handlers.py` guide users through each interaction, build educational prompts, and send results back to the chat. The `gigachat/services.py` module handles OAuth authentication and GigaChat API requests.

Requests have timeouts and bounded retries for transient failures. Mathematical responses can be processed through Pandoc to convert LaTeX; if conversion is unavailable, the original text is used.

Built with Python, `python-telegram-bot`, `aiohttp`, GigaChat, `pypandoc`, and `emoji`.

## Additional and historical modules

The main implementation uses GigaChat. The repository also retains:

- `edu_pal_bot.py` and `services.py` — a standalone Hugging Face implementation. Availability of its legacy endpoint depends on the provider.
- `handlers.py` — alternative conversation handlers.
- `database.py`, `payment.py`, and `analytics.py` — storage, subscription, and analytics modules from an earlier implementation.

Subscriptions, SQLite request tracking, and analytics are not connected to the current `main.py` entry point.

## Checks

```bash
python -m unittest discover -s tests -v
```

Tests cover transient failure retries, stopping retries on permanent errors, the overall timeout, and entry point imports. They do not call live APIs; end-to-end verification requires valid credentials.

## Credentials and data

Provide credentials through environment variables or deployment platform secrets. Keep tokens, local databases, and logs out of Git. These files are excluded through `.gitignore`; request text and provider response bodies must not be written to logs.

User text is sent to GigaChat to generate responses. Do not include passwords, access keys, or other sensitive information in requests. If a credential enters Git history, revoke and replace it with the provider: removing it from the repository does not invalidate it.
