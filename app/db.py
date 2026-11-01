import sqlite3

import click
from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_date TEXT NOT NULL,
    location TEXT NOT NULL,
    guests INTEGER NOT NULL,
    budget REAL NOT NULL,
    currency TEXT NOT NULL,
    style TEXT NOT NULL,
    food_preference TEXT NOT NULL,
    priority TEXT NOT NULL,
    notes TEXT NOT NULL,
    plan TEXT NOT NULL,
    guest_categories TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    task_group TEXT NOT NULL DEFAULT 'timeline'
);
CREATE TABLE IF NOT EXISTS vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    service TEXT NOT NULL,
    priority TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Not Started',
    notes TEXT NOT NULL DEFAULT ''
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db():
    get_db().executescript(SCHEMA)
    get_db().commit()


@click.command("init-db")
def init_db_command():
    init_db()
    click.echo("Initialized the Celebrio database.")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    with app.app_context():
        init_db()
