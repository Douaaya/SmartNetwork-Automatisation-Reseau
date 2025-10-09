# login_window.py
import tkinter as tk
from tkinter import ttk, messagebox
from auth import AuthSystem


class LoginWindow(tk.Toplevel):
    def __init__(self, parent, on_success):
        super().__init__(parent)
        self.title("Connexion - SmartNetwork")
        self.auth = AuthSystem()
        self.on_success = on_success

        # Widgets
        ttk.Label(self, text="Nom d'utilisateur:").grid(row=0, column=0, padx=5, pady=5)
        self.username_entry = ttk.Entry(self)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(self, text="Mot de passe:").grid(row=1, column=0, padx=5, pady=5)
        self.password_entry = ttk.Entry(self, show="*")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(self, text="Se connecter", command=self.attempt_login).grid(row=2, column=1, sticky='e', padx=5)
        ttk.Button(self, text="Créer un compte", command=self.show_signup).grid(row=3, column=1, sticky='e', padx=5)

        # Focus initial
        self.username_entry.focus_set()

    def attempt_login(self):
        user = self.auth.validate_user(
            self.username_entry.get(),
            self.password_entry.get()
        )

        if user:
            self.auth.log_activity(user['id'], "login", "Connexion réussie")
            self.destroy()
            self.on_success(user)  # Callback vers l'application principale
        else:
            messagebox.showerror("Erreur", "Identifiants incorrects ou compte non activé")

    def show_signup(self):
        SignupWindow(self)