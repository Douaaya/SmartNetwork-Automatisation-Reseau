# admin_panel.py
from tkinter import ttk
import sqlite3


class AdminPanel(ttk.Frame):
    def __init__(self, parent, current_user):
        super().__init__(parent)
        self.current_user = current_user
        self.auth = AuthSystem()
        self.setup_ui()

    def setup_ui(self):
        # Onglets
        notebook = ttk.Notebook(self)

        # Onglet Utilisateurs
        users_tab = ttk.Frame(notebook)
        self.setup_users_tab(users_tab)
        notebook.add(users_tab, text="Gestion Utilisateurs")

        # Onglet Activités
        logs_tab = ttk.Frame(notebook)
        self.setup_logs_tab(logs_tab)
        notebook.add(logs_tab, text="Journal des Activités")

        notebook.pack(expand=True, fill='both')

    def setup_users_tab(self, parent):
        # Treeview pour afficher les utilisateurs
        columns = ('id', 'username', 'email', 'role', 'status', 'created_at')
        self.users_tree = ttk.Treeview(parent, columns=columns, show='headings')

        for col in columns:
            self.users_tree.heading(col, text=col.capitalize())
            self.users_tree.column(col, width=100)

        self.users_tree.pack(fill='both', expand=True)

        # Boutons d'action
        btn_frame = ttk.Frame(parent)
        ttk.Button(btn_frame, text="Actualiser", command=self.load_users).pack(side='left')
        ttk.Button(btn_frame, text="Approuver", command=self.approve_selected).pack(side='left')
        ttk.Button(btn_frame, text="Modifier", command=self.edit_user).pack(side='left')
        btn_frame.pack()

        self.load_users()

    def load_users(self):
        conn = sqlite3.connect('network_auth.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role, status, created_at FROM users")

        for row in self.users_tree.get_children():
            self.users_tree.delete(row)

        for user in cursor.fetchall():
            self.users_tree.insert('', 'end', values=user)

    def approve_selected(self):
        selected = self.users_tree.focus()
        if not selected:
            return

        user_data = self.users_tree.item(selected)['values']
        if user_data[4] == 'pending':  # Status
            self.auth.approve_user(user_data[0], self.current_user['id'])
            self.load_users()

    def setup_logs_tab(self, parent):
        # Configuration similaire pour les logs
        pass