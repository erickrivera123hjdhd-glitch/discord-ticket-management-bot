import sqlite3
import time

DB_PATH = "tickets.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS guild_config (
        guild_id INTEGER PRIMARY KEY,
        ticket_panel_message_id INTEGER,
        transcript_log_channel_id INTEGER,
        staff_role_id INTEGER,
        ticket_counter INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS tickets (
        ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        creator_id INTEGER NOT NULL,
        claimed_by INTEGER,
        opened_at INTEGER NOT NULL,
        closed_at INTEGER,
        deleted INTEGER DEFAULT 0
    )""")
    conn.commit()
    conn.close()


def get_guild_config(guild_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM guild_config WHERE guild_id=?", (guild_id,))
    row = c.fetchone()
    conn.close()
    return row


def set_guild_config(guild_id, **kwargs):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO guild_config (guild_id) VALUES (?)", (guild_id,))
    for k, v in kwargs.items():
        c.execute(f"UPDATE guild_config SET {k}=? WHERE guild_id=?", (v, guild_id))
    conn.commit()
    conn.close()


def create_ticket(guild_id, channel_id, category, creator_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    opened = int(time.time())
    c.execute(
        "INSERT INTO tickets (guild_id, channel_id, category, creator_id, opened_at) VALUES (?,?,?,?,?)",
        (guild_id, channel_id, category, creator_id, opened),
    )
    conn.commit()
    conn.close()
    return opened


def get_user_open_ticket(guild_id, user_id, category):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT ticket_id, channel_id FROM tickets WHERE guild_id=? AND creator_id=? AND category=? AND closed_at IS NULL",
        (guild_id, user_id, category),
    )
    row = c.fetchone()
    conn.close()
    return row


def close_ticket(ticket_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    closed = int(time.time())
    c.execute("UPDATE tickets SET closed_at=? WHERE ticket_id=?", (closed, ticket_id))
    conn.commit()
    conn.close()


def delete_ticket(ticket_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE tickets SET deleted=1 WHERE ticket_id=?", (ticket_id,))
    conn.commit()
    conn.close()


def set_claim(ticket_id, staff_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE tickets SET claimed_by=? WHERE ticket_id=?", (staff_id, ticket_id))
    conn.commit()
    conn.close()


def reopen_ticket(ticket_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE tickets SET closed_at=NULL WHERE ticket_id=?", (ticket_id,))
    conn.commit()
    conn.close()


def get_ticket(ticket_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,))
    row = c.fetchone()
    conn.close()
    return row


def get_ticket_by_channel(guild_id, channel_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT ticket_id, channel_id, category, creator_id, claimed_by, opened_at, closed_at FROM tickets WHERE guild_id=? AND channel_id=? AND closed_at IS NULL",
        (guild_id, channel_id),
    )
    row = c.fetchone()
    conn.close()
    return row
