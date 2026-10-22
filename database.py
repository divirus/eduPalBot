import sqlite3
from datetime import datetime
import os
from config import DB_PATH  # Import the path from config.py
import logging

logger = logging.getLogger(__name__)

def init_db():
    conn = sqlite3.connect(DB_PATH)  # Shared database path
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_start_time TEXT,
                    last_start_time TEXT,
                    subscribed INTEGER DEFAULT 0,
                    subscription_expiration TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    request_text TEXT,
                    request_time TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id))''')
    conn.commit()
    conn.close()

def update_db_schema():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('ALTER TABLE users ADD COLUMN first_start_time TEXT')
    except sqlite3.OperationalError:
        pass  # The column already exists
    try:
        c.execute('ALTER TABLE users ADD COLUMN last_start_time TEXT')
    except sqlite3.OperationalError:
        pass  # The column already exists
    conn.commit()
    conn.close()

def increment_request_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    c.execute("UPDATE users SET request_count = request_count + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def log_request(user_id, request_text, request_time):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO requests (user_id, request_text, request_time) VALUES (?, ?, ?)",
              (user_id, request_text, request_time))
    conn.commit()
    conn.close()

def is_subscribed_to_bot(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT subscribed FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def subscribe_user(user_id, expiration_date=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    c.execute("UPDATE users SET subscribed = 1, subscription_expiration = ? WHERE user_id = ?", (expiration_date, user_id))
    conn.commit()
    conn.close()

def unsubscribe_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET subscribed = 0, subscription_expiration = NULL WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def check_db_initialized():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        users_table = c.fetchone()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='requests'")
        requests_table = c.fetchone()
        if users_table and requests_table:
            logger.info("Таблицы 'users' и 'requests' существуют в базе данных")
            return True
        else:
            logger.error("Одна или обе таблицы ('users', 'requests') отсутствуют")
            return False
    except sqlite3.Error as e:
        logger.error(f"Ошибка при проверке базы данных: {e}")
        return False
    finally:
        conn.close()

# Initialize the database and update its schema at startup
init_db()
update_db_schema()