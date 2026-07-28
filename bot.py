"""
BookRecBot — recommends a book based on a genre you send it.

Commands:
  /start              Welcome message + instructions
  /help               Show usage instructions
  /privacy            Show the bot's privacy policy (required for Ads review)
  /genres             List all available genres
  /recommend <genre>  Get a book recommendation for that genre

You can also just type a genre name directly (e.g. "fantasy") without
using the /recommend command.

Recommendations are picked at random from a curated list per genre, and the
bot avoids repeating the same book twice in a row for the same user/genre.
"""

import logging
import os
import sqlite3
from random import choice

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from books_data import BOOKS, GENRE_LABELS, normalize_genre

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_PATH = os.environ.get("DB_PATH", "bookrec.db")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS last_recommendation (
            chat_id INTEGER NOT NULL,
            genre TEXT NOT NULL,
            title TEXT NOT NULL,
            PRIMARY KEY (chat_id, genre)
        )
        """
    )
    conn.commit()
    return conn


def get_last_title(chat_id: int, genre: str):
    conn = db_connect()
    row = conn.execute(
        "SELECT title FROM last_recommendation WHERE chat_id = ? AND genre = ?",
        (chat_id, genre),
    ).fetchone()
    conn.close()
    return row[0] if row else None


def set_last_title(chat_id: int, genre: str, title: str):
    conn = db_connect()
    conn.execute(
        "INSERT INTO last_recommendation (chat_id, genre, title) VALUES (?, ?, ?) "
        "ON CONFLICT(chat_id, genre) DO UPDATE SET title = excluded.title",
        (chat_id, genre, title),
    )
    conn.commit()
    conn.close()


WELCOME_TEXT = (
    "📚 Hi! I'm *BookRecBot*.\n\n"
    "Tell me a genre and I'll recommend a book. Try one of these:\n"
    "`fantasy`, `mystery`, `romance`, `thriller`, `horror`, `sci-fi`\n\n"
    "See the full list anytime with /genres\n\n"
    "Other commands:\n"
    "/recommend <genre> — same as just typing the genre\n"
    "/help — show this again\n"
    "/privacy — privacy policy"
)

PRIVACY_TEXT = (
    "🔒 *Privacy Policy*\n\n"
    "BookRecBot stores only your Telegram chat ID and the last book "
    "recommended to you per genre, so we can avoid repeating the same book "
    "twice in a row. We do not collect names, phone numbers, reading "
    "history beyond that, or any other personal data, and we do not share "
    "data with third parties.\n\n"
    "If you'd like your data removed, message the bot owner."
)


def format_genre_list() -> str:
    lines = ["📖 *Available genres:*"]
    for label in sorted(GENRE_LABELS.values()):
        lines.append(f"• {label}")
    lines.append("\nJust type any of these (or use /recommend <genre>).")
    return "\n".join(lines)


def get_recommendation(chat_id: int, genre_key: str) -> str:
    books = BOOKS[genre_key]
    last_title = get_last_title(chat_id, genre_key)

    candidates = [b for b in books if b["title"] != last_title] or books
    book = choice(candidates)

    set_last_title(chat_id, genre_key, book["title"])

    label = GENRE_LABELS[genre_key]
    return (
        f"📚 *{label} recommendation:*\n\n"
        f"*{book['title']}* by {book['author']}\n"
        f"{book['blurb']}\n\n"
        f"Want another? Just send `{label.lower()}` again."
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT, parse_mode="Markdown")


async def privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(PRIVACY_TEXT, parse_mode="Markdown")


async def genres_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_genre_list(), parse_mode="Markdown")


async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Please tell me a genre, e.g. `/recommend fantasy`",
            parse_mode="Markdown",
        )
        return
    genre_text = " ".join(context.args)
    await handle_genre_request(update, genre_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    await handle_genre_request(update, text)


async def handle_genre_request(update: Update, genre_text: str):
    genre_key = normalize_genre(genre_text)
    chat_id = update.effective_chat.id

    if genre_key not in BOOKS:
        await update.message.reply_text(
            "I don't recognize that genre. Here's what I can recommend:\n\n"
            + format_genre_list(),
            parse_mode="Markdown",
        )
        return

    reply = get_recommendation(chat_id, genre_key)
    await update.message.reply_text(reply, parse_mode="Markdown")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    db_connect().close()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("privacy", privacy_command))
    application.add_handler(CommandHandler("genres", genres_command))
    application.add_handler(CommandHandler("recommend", recommend_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("BookRecBot starting (polling mode)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
