# models.py
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash


def init_db():
    conn = sqlite3.connect('network_auth.db')
    c = conn.cursor()

    # Table Utilisateurs
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE NOT NULL,
                 password_hash TEXT NOT NULL,
                 email TEXT,
                 role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
                 status TEXT NOT NULL CHECK (status IN ('pending', 'active', 'inactive')),
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 last_login TIMESTAMP,
                 permissions TEXT)''')  # JSON serialized list

    # Table Journal des Activités
    c.execute('''CREATE TABLE IF NOT EXISTS activity_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 action_type TEXT,
                 target_device TEXT,
                 details TEXT,
                 FOREIGN KEY(user_id) REFERENCES users(id))''')

    # Créer l'admin par défaut si inexistant
    c.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    if c.fetchone()[0] == 0:
        admin_pass = generate_password_hash("admin123")  # À changer immédiatement après
        c.execute("INSERT INTO users (username, password_hash, role, status) VALUES (?, ?, ?, ?)",
                  ("admin", admin_pass, "admin", "active"))

    conn.commit()
    conn.close()