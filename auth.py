# auth.py
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3


class AuthSystem:
    def __init__(self):
        self.conn = sqlite3.connect('network_auth.db')

    def validate_user(self, username, password):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, password_hash, role, status FROM users WHERE username=?", (username,))
        user = cursor.fetchone()

        if not user:
            return None  # Utilisateur inexistant
        if not check_password_hash(user[1], password):
            return None  # Mot de passe incorrect
        if user[3] != 'active':
            return None  # Compte non activé

        return {'id': user[0], 'username': username, 'role': user[2]}

    def create_user(self, username, password, email, role='user'):
        """Soumission pour approbation admin"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash, email, role, status) VALUES (?, ?, ?, ?, ?)",
                (username, generate_password_hash(password), email, role, 'pending')
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Username déjà pris

    def approve_user(self, user_id, admin_id):
        """Approbation par l'admin"""
        self.log_activity(admin_id, "user_approval", f"Approved user {user_id}")
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET status='active' WHERE id=?", (user_id,))
        self.conn.commit()

    def log_activity(self, user_id, action_type, details, target=None):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO activity_log (user_id, action_type, target_device, details) VALUES (?, ?, ?, ?)",
            (user_id, action_type, target, details)
        )
        self.conn.commit()