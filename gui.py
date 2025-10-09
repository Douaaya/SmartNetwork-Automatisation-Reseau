import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog, filedialog
import threading
import os
import pandas as pd
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
from datetime import datetime
import scan_reseau
import backup
import configurations
import openpyxl
import queue
from scan_reseau import NetworkScanner
from chat_frame import ModernChatFrame
from backup import BackupManager, SFTPManager


class ModernNetworkAutomationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SmartNetwork")
        self.root.geometry("1280x800")
        self.root.minsize(1024, 768)
        self.root.maxsize(1200, 800)  # Taille fixe

        # Empêcher le redimensionnement
        self.root.resizable(False, False)

        # Configuration initiale
        self._setup_styles()
        self.chemin_equipement = ""
        self.chemin_configurations = ""
        self.chemin_backup = ""

        # Configuration spécifique au chat
        self.chat_history = []
        self.is_processing = False

        # Structure principale
        self.main_container = ttk.Frame(root)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Création des composants
        self._create_modern_sidebar()
        self._create_status_bar()

        # Zone de contenu principal
        self.content = ttk.Frame(self.main_container, style='Content.TFrame')
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Initialisation des pages
        self.frames = {}
        pages = [
            ModernHomeFrame,
            ModernScanFrame,
            ModernBackupFrame,
            ModernConfigFrame,
            ModernCheckFrame,
            ModernChatFrame
        ]

        for page in pages:
            frame = page(self.content, self)
            self.frames[page] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Démarrer sur la page d'accueil
        self.show_home()

        # Raccourcis clavier
        self._setup_keyboard_shortcuts()

    def _setup_styles(self):
        """Configure tous les styles visuels"""
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Styles globaux
        self.style.configure('.', background='#f8f9fa', foreground='#1f2937', font=('Segoe UI', 10))
        self.style.configure('TFrame', background='#f8f9fa')
        self.style.configure('TLabel', background='#f8f9fa', font=('Segoe UI', 10))
        self.style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'), foreground='#2c3e50')
        self.style.configure('TButton', font=('Segoe UI', 10), padding=8)

        # Barre latérale
        self.style.configure('Sidebar.TFrame', background='#343a40')
        self.style.configure('Sidebar.TLabel', background='#343a40', foreground='white',
                             font=('Segoe UI', 12, 'bold'))
        self.style.configure('Sidebar.TButton', font=('Segoe UI', 11), padding=12,
                             foreground='white', background='#495057', width=18, anchor='w')
        self.style.map('Sidebar.TButton', background=[('active', '#007bff'), ('pressed', '#0056b3')])
        self.style.configure('Active.TButton', background='#007bff', foreground='white')

        # Boutons
        self.style.configure('Primary.TButton', font=('Segoe UI', 10, 'bold'), padding=8,
                             foreground='white', background='#28a745')
        self.style.map('Primary.TButton',
                       foreground=[('active', 'white'), ('!disabled', 'white')],
                       background=[('active', '#218838'), ('!disabled', '#28a745')])
        self.style.configure('Danger.TButton', font=('Segoe UI', 10, 'bold'), padding=8,
                             foreground='white', background='#dc3545')
        self.style.configure('Info.TButton', font=('Segoe UI', 10, 'bold'), padding=8,
                             foreground='white', background='#17a2b8')

        # Style spécifique au chat
        self.style.configure('Arrow.TButton', font=('Segoe UI', 14), foreground='white',
                             background='#3b82f6', borderwidth=0, width=3)
        self.style.map('Arrow.TButton', background=[('active', '#2563eb')])

        # Contenu
        self.style.configure('Content.TFrame', background='white', relief=tk.FLAT, borderwidth=0)
        self.style.configure('Card.TFrame', background='white', relief=tk.RAISED,
                             borderwidth=1, padding=10)
        self.style.configure('Input.TFrame', background='#f3f4f6')

        # Barre de statut
        self.style.configure('Status.TFrame', background='#343a40')
        self.style.configure('Status.TLabel', font=('Segoe UI', 9),
                             background='#343a40', foreground='white')

        # Zone de texte
        self.style.configure('Modern.TText', font=('Consolas', 10), background='#f8f9fa')

        # Style des messages du chat
        self.style.configure('User.TLabel', background='#dbeafe', foreground='#1e40af',
                             font=('Segoe UI', 11), padding=10, relief='flat', borderwidth=0,
                             wraplength=600, anchor='e')
        self.style.configure('Assistant.TLabel', background='#ecfdf5', foreground='#065f46',
                             font=('Segoe UI', 11), padding=10, relief='flat', borderwidth=0,
                             wraplength=600, anchor='w')
        self.style.configure('System.TLabel', background='#f3f4f6', foreground='#6b7280',
                             font=('Segoe UI', 9, 'italic'), padding=5)

        # Barre de progression
        self.style.configure('TProgressbar', thickness=5, troughcolor='#e5e7eb',
                             background='#3b82f6', lightcolor='#93c5fd', darkcolor='#1d4ed8')

        # Champs de saisie
        self.style.configure('Modern.TEntry', fieldbackground='white', foreground='#1f2937',
                             bordercolor='#e5e7eb', lightcolor='#e5e7eb', darkcolor='#e5e7eb',
                             padding=10)
        self.style.map('Modern.TEntry',
                       bordercolor=[('focus', '#3b82f6'), ('!focus', '#e5e7eb')],
                       lightcolor=[('focus', '#3b82f6'), ('!focus', '#e5e7eb')],
                       darkcolor=[('focus', '#3b82f6'), ('!focus', '#e5e7eb')])
        # Ajoutez ces nouveaux styles pour les boutons bleus et rouges
        self.style.configure('Blue.TButton', foreground='white', background='#3b82f6')
        self.style.map('Blue.TButton',
                       foreground=[('active', 'white'), ('!disabled', 'white')],
                       background=[('active', '#2563eb'), ('!disabled', '#3b82f6')])

        self.style.configure('Red.TButton', foreground='white', background='#dc3545')
        self.style.map('Red.TButton',
                       foreground=[('active', 'white'), ('!disabled', 'white')],
                       background=[('active', '#c82333'), ('!disabled', '#dc3545')])

        # Style pour le header
        self.style.configure('Header.TFrame', background='#f8f9fa')

        # Style pour le titre principal
        self.style.configure('Title.TLabel',
                             font=('Segoe UI', 18, 'bold'),
                             foreground='#2c3e50',
                             anchor='w')  # Alignement à gauche

        # Style pour la sidebar
        self.style.configure('Sidebar.TFrame', background='#343a40')

        # Style pour les labels de la sidebar
        self.style.configure('Sidebar.TLabel',
                             background='#343a40',
                             font=('Segoe UI', 12, 'bold'),
                             padding=5)

        """Configure tous les styles visuels"""
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Styles globaux
        self.style.configure('.', background='#f8f9fa', foreground='#1f2937', font=('Segoe UI', 10))
        self.style.configure('TFrame', background='#f8f9fa')
        self.style.configure('TLabel', background='#f8f9fa', font=('Segoe UI', 10))
        self.style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'), foreground='#2c3e50')
        self.style.configure('TButton', font=('Segoe UI', 10), padding=8)

        # Barre latérale
        self.style.configure('Sidebar.TFrame', background='#343a40')
        self.style.configure('Sidebar.TLabel', background='#343a40', foreground='white',
                             font=('Segoe UI', 12, 'bold'))
        self.style.configure('Sidebar.TButton', font=('Segoe UI', 11), padding=12,
                             foreground='white', background='#495057', width=18, anchor='w')
        self.style.map('Sidebar.TButton', background=[('active', '#007bff'), ('pressed', '#0056b3')])
        self.style.configure('Active.TButton', background='#007bff', foreground='white')

        # Boutons
        self.style.configure('Primary.TButton', font=('Segoe UI', 10, 'bold'), padding=8,
                             foreground='white', background='#28a745')
        self.style.map('Primary.TButton',
                       foreground=[('active', 'white'), ('!disabled', 'white')],
                       background=[('active', '#218838'), ('!disabled', '#28a745')])
        self.style.configure('Danger.TButton', font=('Segoe UI', 10, 'bold'), padding=8,
                             foreground='white', background='#dc3545')
        self.style.configure('Info.TButton', font=('Segoe UI', 10, 'bold'), padding=8,
                             foreground='white', background='#17a2b8')

        # Style spécifique au chat
        self.style.configure('Arrow.TButton', font=('Segoe UI', 14), foreground='white',
                             background='#3b82f6', borderwidth=0, width=3)
        self.style.map('Arrow.TButton', background=[('active', '#2563eb')])

        # Contenu
        self.style.configure('Content.TFrame', background='white', relief=tk.FLAT, borderwidth=0)
        self.style.configure('Card.TFrame', background='white', relief=tk.RAISED,
                             borderwidth=1, padding=10)
        self.style.configure('Input.TFrame', background='#f3f4f6')

        # Barre de statut
        self.style.configure('Status.TFrame', background='#343a40')
        self.style.configure('Status.TLabel', font=('Segoe UI', 9),
                             background='#343a40', foreground='white')

        # Zone de texte
        self.style.configure('Modern.TText', font=('Consolas', 10), background='#f8f9fa')

        # Style des messages du chat
        self.style.configure('User.TLabel', background='#dbeafe', foreground='#1e40af',
                             font=('Segoe UI', 11), padding=10, relief='flat', borderwidth=0,
                             wraplength=600, anchor='e')
        self.style.configure('Assistant.TLabel', background='#ecfdf5', foreground='#065f46',
                             font=('Segoe UI', 11), padding=10, relief='flat', borderwidth=0,
                             wraplength=600, anchor='w')
        self.style.configure('System.TLabel', background='#f3f4f6', foreground='#6b7280',
                             font=('Segoe UI', 9, 'italic'), padding=5)

        # Barre de progression
        self.style.configure('TProgressbar', thickness=5, troughcolor='#e5e7eb',
                             background='#3b82f6', lightcolor='#93c5fd', darkcolor='#1d4ed8')

        # Champs de saisie
        self.style.configure('Modern.TEntry', fieldbackground='white', foreground='#1f2937',
                             bordercolor='#e5e7eb', lightcolor='#e5e7eb', darkcolor='#e5e7eb',
                             padding=10)
        self.style.map('Modern.TEntry',
                       bordercolor=[('focus', '#3b82f6'), ('!focus', '#e5e7eb')],
                       lightcolor=[('focus', '#3b82f6'), ('!focus', '#e5e7eb')],
                       darkcolor=[('focus', '#3b82f6'), ('!focus', '#e5e7eb')])
        # Ajoutez ces nouveaux styles pour les boutons bleus et rouges
        self.style.configure('Blue.TButton', foreground='white', background='#3b82f6')
        self.style.map('Blue.TButton',
                       foreground=[('active', 'white'), ('!disabled', 'white')],
                       background=[('active', '#2563eb'), ('!disabled', '#3b82f6')])

        self.style.configure('Red.TButton', foreground='white', background='#dc3545')
        self.style.map('Red.TButton',
                       foreground=[('active', 'white'), ('!disabled', 'white')],
                       background=[('active', '#c82333'), ('!disabled', '#dc3545')])

        # Style pour le header
        self.style.configure('Header.TFrame', background='#f8f9fa')

        # Style pour le titre principal
        self.style.configure('Title.TLabel',
                             font=('Segoe UI', 18, 'bold'),
                             foreground='#2c3e50',
                             anchor='w')  # Alignement à gauche

        # Style pour la sidebar
        self.style.configure('Sidebar.TFrame', background='#343a40')

        # Style pour les labels de la sidebar
        self.style.configure('Sidebar.TLabel',
                             background='#343a40',
                             font=('Segoe UI', 12, 'bold'),
                             padding=5)

        # Style pour les cartes
        self.style.configure('Card.TFrame',
                             background='white',
                             borderwidth=1,
                             relief='solid',
                             bordercolor='#e5e7eb')

        # Style personnalisé pour la barre de progression
        self.style.configure('Custom.Horizontal.TProgressbar',
                             troughcolor='#e5e7eb',
                             background='#3b82f6',
                             thickness=10,
                             bordercolor='#e5e7eb',
                             lightcolor='#3b82f6',
                             darkcolor='#3b82f6')

        # Style pour les onglets
        self.style.configure('Custom.TNotebook', background='#f8f9fa')
        self.style.configure('Custom.TNotebook.Tab',
                             padding=[10, 5],
                             background='#e5e7eb',
                             font=('Segoe UI', 9))
        self.style.map('Custom.TNotebook.Tab',
                       background=[('selected', 'white')],
                       expand=[('selected', [1, 1, 1, 0])])

        # Style pour les indicateurs de statut
        self.style.configure('Status.TLabel', font=('Segoe UI', 9))
        self.style.map('Status.TLabel',
                       foreground=[('!active', '#6c757d'), ('active', '#28a745')])




    def _create_modern_sidebar(self):
        """Crée la barre latérale moderne"""
        self.sidebar = ttk.Frame(self.main_container, width=250, style='Sidebar.TFrame')
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Logo
        logo_frame = ttk.Frame(self.sidebar, style='Sidebar.TFrame')
        logo_frame.pack(pady=(20, 30), padx=10, fill=tk.X)

        scan_label = ttk.Label(logo_frame,
                               text="Smart",
                               style='Sidebar.TLabel',
                               font=('Segoe UI', 16, 'bold'),
                               foreground='white')  # Texte blanc
        scan_label.pack(side=tk.LEFT)

        # "Network" en bleu
        network_label = ttk.Label(logo_frame,
                                  text="Network",
                                  style='Sidebar.TLabel',
                                  font=('Segoe UI', 16, 'bold'),
                                  foreground='#17a2b8')  # Texte bleu
        network_label.pack(side=tk.LEFT)

        # Menu
        menu_options = [
            ("🏠 Accueil", self.show_home),
            ("🔍 Scan Réseau", self.show_scan),
            ("💾 Backup", self.show_backup),
            ("⚙️ Configuration", self.show_config),
            ("✅ Vérification", self.show_check),
            ("🤖 Assistant Réseau", self.show_chat),
        ]

        for text, command in menu_options:
            btn = ttk.Button(self.sidebar, text=text, command=command,
                             style='Sidebar.TButton')
            btn.pack(fill=tk.X, padx=10, pady=5)
            setattr(self, f"btn_{text.split()[1].lower()}", btn)

    def _create_status_bar(self):
        """Crée la barre de statut"""
        self.status_var = tk.StringVar(value="Prêt")
        status_bar = ttk.Frame(self.main_container, style='Status.TFrame')
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Label(status_bar, textvariable=self.status_var, style='Status.TLabel').pack(side=tk.LEFT, padx=10)
        ttk.Label(status_bar, text="v2.0", style='Status.TLabel').pack(side=tk.RIGHT, padx=10)

    def _setup_keyboard_shortcuts(self):
        """Configure les raccourcis clavier"""
        self.root.bind('<Control-n>', lambda e: self.show_scan())
        self.root.bind('<Control-b>', lambda e: self.show_backup())
        self.root.bind('<Control-a>', lambda e: self.show_chat())

    def set_chemin_excel(self, chemin):
        self.chemin_equipement = chemin
        self.update_all_displays()

    def set_chemin_config(self, chemin):
        self.chemin_configurations = chemin
        self.update_all_displays()

    def set_chemin_backup(self, chemin):
        self.chemin_backup = chemin
        self.update_all_displays()

    def update_all_displays(self):
        for frame in self.frames.values():
            if hasattr(frame, 'update_path_display'):
                frame.update_path_display()

    def show_home(self):
        self._show_frame(ModernHomeFrame, self.btn_accueil)
        self.update_status("Page d'accueil - Prêt à configurer les chemins")

    def show_scan(self):
        # On permet toujours l'accès à la page scan
        self._show_frame(ModernScanFrame, self.btn_scan)

    def show_backup(self):
        self._show_frame(ModernBackupFrame, self.btn_backup)

    def show_config(self):
        self._show_frame(ModernConfigFrame, self.btn_configuration)

    def show_check(self):
        self._show_frame(ModernCheckFrame, self.btn_vérification)

    def show_chat(self):
        self._show_frame(ModernChatFrame, self.btn_assistant)

    def _show_frame(self, frame_class, button):
        """Méthode helper pour afficher un frame"""
        self.update_active_button(button)
        frame = self.frames[frame_class]
        frame.tkraise()
        if hasattr(frame, 'on_show'):
            frame.on_show()
        self.update_status(f"{frame_class.__name__[6:-5]} - Prêt")

    def update_active_button(self, active_button):
        """Met à jour l'apparence du bouton actif"""
        for btn in [self.btn_accueil, self.btn_scan, self.btn_backup,
                    self.btn_configuration, self.btn_vérification, self.btn_assistant]:
            if btn == active_button:
                btn.config(style='Active.TButton')
            else:
                btn.config(style='Sidebar.TButton')

    def update_status(self, message):
        """Met à jour le message de statut"""
        self.status_var.set(message)
        self.root.update_idletasks()


class ModernHomeFrame(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, style='Content.TFrame')
        self.controller = controller

        container = ttk.Frame(self, style='Content.TFrame')
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header avec titre et logo - NOUVELLE VERSION
        header_frame = ttk.Frame(container, style='Content.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))

        # Titre à gauche
        title_frame = ttk.Frame(header_frame, style='Content.TFrame')
        title_frame.pack(side=tk.LEFT, expand=True)

        title = ttk.Label(title_frame,
                          text="Gestion des équipements réseau",
                          style='Title.TLabel',
                          font=('Segoe UI', 18, 'bold'))
        title.pack()

        # Logo OCP à droite - NOUVELLE POSITION
        logo_container = tk.Frame(header_frame, bg='white')
        logo_container.pack(side=tk.RIGHT, padx=10)

        try:
            logo_path = "D:\\MON stage pfe\\OCP Group_s_1.png"
            self.ocp_logo = tk.PhotoImage(file=logo_path)
            self.ocp_logo = self.ocp_logo.subsample(2, 2)
            logo_label = tk.Label(logo_container,
                                  image=self.ocp_logo,
                                  bg='white')
            logo_label.image = self.ocp_logo
            logo_label.pack()
        except Exception as e:
            print(f"Erreur chargement logo: {e}")
            placeholder = tk.Label(logo_container,
                                   text="LOGO OCP",
                                   bg='white',
                                   fg='black')
            placeholder.pack()

        card = ttk.Frame(container, style='Card.TFrame')
        card.pack(fill=tk.BOTH, expand=True, pady=10)

        # title = ttk.Label(card, text="Configuration des chemins", style='Title.TLabel')
        # title.pack(pady=(0, 20))

        form_frame = ttk.Frame(card, style='Card.TFrame')
        form_frame.pack(fill=tk.X, pady=10)

        self.excel_path = tk.StringVar()
        self.config_path = tk.StringVar()
        self.backup_path = tk.StringVar()

        self._create_form_field(form_frame, "Fichier Excel des équipements:", 0,
                                self.excel_path, self.select_excel)

        btn_frame = ttk.Frame(card, style='Card.TFrame')
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="Vérifier chemin", command=self.verify_paths,
                   style='Primary.TButton').pack(side=tk.LEFT, padx=5)

        info_card = ttk.Frame(card, style='Card.TFrame')
        info_card.pack(fill=tk.BOTH, expand=True, pady=10)

        ttk.Label(info_card, text="Journal des opérations:", style='TLabel').pack(anchor=tk.W)

        self.info_text = scrolledtext.ScrolledText(
            info_card,
            width=80,
            height=10,
            wrap=tk.WORD,
            font=('Segoe UI', 10),
            padx=10,
            pady=10,
            background='#f8f9fa',
            relief=tk.FLAT
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)

        welcome_msg = """        Bienvenue dans SmartNetwork


    • Sélectionnez le fichier nécessaire ci-dessus

      NB: les colonnes de fichiers doivent obligatoirement contenir les noms suivants:
        Hostname, IP Address, Device Type (cisco_ios) et Configurer (Y ou N)
        Commencer votre tableau à partir de la troisième ligne dans Excel

    • Utilisez le menu de gauche pour naviguer

    • Consultez les journaux pour le suivi des opérations"""

        self.info_text.insert(tk.END, welcome_msg)
        self.info_text.config(state=tk.DISABLED)
        self.update_path_display()

    def _create_form_field(self, parent, label_text, row, var, command):
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill=tk.X, pady=5)

        ttk.Label(frame, text=label_text, style='TLabel').pack(side=tk.LEFT, padx=5)

        entry = ttk.Entry(frame, textvariable=var, width=60, font=('Segoe UI', 10))
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Button(frame, text="Parcourir...", command=command,
                   style='Primary.TButton').pack(side=tk.RIGHT, padx=5)

    def update_path_display(self):
        if hasattr(self.controller, 'chemin_equipement'):
            self.excel_path.set(self.controller.chemin_equipement)
        if hasattr(self.controller, 'chemin_configurations'):
            self.config_path.set(self.controller.chemin_configurations)
        if hasattr(self.controller, 'chemin_backup'):
            self.backup_path.set(self.controller.chemin_backup)

    def on_show(self):
        self.controller.update_status("Prêt à configurer les chemins")
        self.update_path_display()

    def select_excel(self):
        fichier = filedialog.askopenfilename(
            title="Sélectionner le fichier Excel",
            filetypes=[("Fichiers Excel", "*.xlsx *.xls"), ("Tous les fichiers", "*.*")]
        )
        if fichier:
            self.controller.set_chemin_excel(fichier)
            self.log_message(f"Fichier Excel sélectionné: {fichier}")

    def select_config(self):
        fichier = filedialog.askopenfilename(
            title="Sélectionner le fichier de configuration",
            filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")]
        )
        if fichier:
            self.controller.set_chemin_config(fichier)
            self.log_message(f"Fichier de configuration sélectionné: {fichier}")

    def select_backup(self):
        dossier = filedialog.askdirectory(
            title="Sélectionner le dossier de backup"
        )
        if dossier:
            self.controller.set_chemin_backup(dossier)
            self.log_message(f"Dossier de backup sélectionné: {dossier}")

    def verify_paths(self):
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)

        if hasattr(self.controller, 'chemin_equipement') and self.controller.chemin_equipement:
            self.info_text.insert(tk.END, f"✅ Fichier Excel: {self.controller.chemin_equipement}\n")
        else:
            self.info_text.insert(tk.END, "❌ Aucun fichier Excel sélectionné\n")

        self.info_text.config(state=tk.DISABLED)

    def log_message(self, message):
        self.info_text.config(state=tk.NORMAL)
        self.info_text.insert(tk.END, f"{message}\n")
        self.info_text.see(tk.END)
        self.info_text.config(state=tk.DISABLED)


class ModernScanFrame(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, style='Content.TFrame')
        self.controller = controller
        self.scanner = NetworkScanner()
        self.current_results = None
        self.scan_thread = None
        self.stop_scan_flag = False
        self.current_scan_target = None
        self.is_scanning = False  # Nouvelle variable pour suivre l'état du scan

        # Variables pour les options
        self.disable_dns = tk.BooleanVar(value=True)
        self.privileged = tk.BooleanVar(value=True)

        # Setup UI
        self.setup_ui()
        self.scanner.load_config()
        self.setup_tooltips()

    def setup_ui(self):
        """Configure l'interface utilisateur"""
        container = ttk.Frame(self, style='Content.TFrame')
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header
        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(header, text="🔍 Analyse Réseau Avancée", style='Title.TLabel').pack(side=tk.LEFT)

        # Section aide - MODIFIÉ
        help_frame = ttk.LabelFrame(container, text="Aide & Explications", style='Card.TFrame')
        help_frame.pack(fill=tk.X, pady=(0, 10))

        help_text = """
        Cette page permet d'analyser votre réseau à l'aide de Nmap.
        - Nmap doit être installé sur votre système
        - Les droits administrateur sont nécessaires pour certains types de scan
        """
        ttk.Label(help_frame, text=help_text, style='TLabel').pack(padx=5, pady=5, anchor='w')

        # Section configuration
        config_frame = ttk.LabelFrame(container, text="Configuration du Scan", style='Card.TFrame')
        config_frame.pack(fill=tk.X, pady=10)

        # Type de scan
        ttk.Label(config_frame, text="Type de Scan:").grid(row=0, column=0, padx=5, sticky='e')
        self.scan_type = ttk.Combobox(
            config_frame,
            values=list(self.scanner.default_config['scan_types'].keys()),
            state='readonly'
        )
        self.scan_type.current(0)
        self.scan_type.grid(row=0, column=1, padx=5, sticky='ew')

        # Info sur le scan sélectionné
        self.scan_info = ttk.Label(config_frame, text="", style='Info.TLabel')
        self.scan_info.grid(row=1, column=0, columnspan=2, padx=5, sticky='w')

        # Options avancées
        ttk.Label(config_frame, text="Options:").grid(row=2, column=0, padx=5, sticky='e')
        self.advanced_options = ttk.Frame(config_frame)
        self.advanced_options.grid(row=2, column=1, padx=5, sticky='ew')

        self.disable_dns_checkbtn = ttk.Checkbutton(
            self.advanced_options,
            text="Désactiver DNS",
            variable=self.disable_dns,
            command=self.update_scan_info
        )
        self.disable_dns_checkbtn.pack(side=tk.LEFT)

        self.privileged_checkbtn = ttk.Checkbutton(
            self.advanced_options,
            text="Mode privilégié",
            variable=self.privileged,
            command=self.update_scan_info
        )
        self.privileged_checkbtn.pack(side=tk.LEFT)

        # Section cibles
        target_frame = ttk.LabelFrame(container, text="Cibles à Scanner", style='Card.TFrame')
        target_frame.pack(fill=tk.X, pady=10)

        # Onglets pour les différentes méthodes
        self.notebook = ttk.Notebook(target_frame)
        self.notebook.pack(fill=tk.X, padx=5, pady=5)

        # Onglet Excel
        excel_tab = ttk.Frame(self.notebook)
        self.notebook.add(excel_tab, text="Depuis Excel")

        ttk.Label(excel_tab, text="Fichier Excel défini dans la page Accueil").pack(pady=5)
        self.excel_status = ttk.Label(excel_tab, text="Aucun fichier sélectionné", style='Warning.TLabel')
        self.excel_status.pack(pady=5)

        # Onglet Plage IP
        range_tab = ttk.Frame(self.notebook)
        self.notebook.add(range_tab, text="Plage IP")

        ttk.Label(range_tab, text="IP Début:").grid(row=0, column=0, padx=5, pady=5)
        self.start_ip = ttk.Entry(range_tab, width=15)
        self.start_ip.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(range_tab, text="IP Fin:").grid(row=0, column=2, padx=5, pady=5)
        self.end_ip = ttk.Entry(range_tab, width=15)
        self.end_ip.grid(row=0, column=3, padx=5, pady=5)

        # Boutons d'action
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill=tk.X, pady=10)

        self.start_btn = ttk.Button(  # Changé pour stocker la référence
            btn_frame,
            text="Démarrer Scan",
            command=self.start_scan,
            style='Primary.TButton'
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(  # Changé pour stocker la référence
            btn_frame,
            text="Arrêter Scan",
            command=self.stop_scan,
            style='Danger.TButton',
            state=tk.DISABLED  # Désactivé par défaut
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Exporter Résultats",
            command=self.export_results,
            style='Info.TButton'
        ).pack(side=tk.RIGHT, padx=5)

        # Résultats - MODIFICATION DU SCROLLTEXT
        results_frame = ttk.LabelFrame(container, text="Résultats", style='Card.TFrame')
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Treeview pour affichage tabulaire
        self.tree = ttk.Treeview(
            results_frame,
            columns=('hostname', 'ip', 'status', 'details'),
            show='headings',
            selectmode='browse'
        )
        self.tree.heading('hostname', text='Hostname')
        self.tree.heading('ip', text='IP')
        self.tree.heading('status', text='Statut')
        self.tree.heading('details', text='Détails')

        self.tree.column('hostname', width=150)
        self.tree.column('ip', width=120)
        self.tree.column('status', width=80)
        self.tree.column('details', width=250)

        # Configuration du scroll pour le Treeview
        vsb = ttk.Scrollbar(results_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(results_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        # Journal d'activité - MODIFICATION POUR LE SCROLL
        log_frame = ttk.LabelFrame(container, text="Journal d'activité", style='Card.TFrame')
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Remplacement du ScrolledText par un Text standard avec scrollbar
        self.log_text = tk.Text(
            log_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            padx=10,
            pady=10,
            background='#f8f9fa',
            relief=tk.FLAT,
            state='normal'
        )

        log_vsb = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_hsb = ttk.Scrollbar(log_frame, orient="horizontal", command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=log_vsb.set, xscrollcommand=log_hsb.set)

        self.log_text.grid(row=0, column=0, sticky='nsew')
        log_vsb.grid(row=0, column=1, sticky='ns')
        log_hsb.grid(row=1, column=0, sticky='ew')

        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        # Détails dans une fenêtre séparée
        self.details_window = None

        # Barre de progression
        self.progress = ttk.Progressbar(results_frame, mode='indeterminate')

        # Configuration du redimensionnement
        results_frame.grid_rowconfigure(0, weight=1)
        results_frame.grid_columnconfigure(0, weight=1)

        # Événements
        self.scan_type.bind('<<ComboboxSelected>>', self.update_scan_info)
        self.tree.bind('<Double-1>', self.show_details_window)

    def setup_tooltips(self):
        """Configure les infobulles pour les options"""
        from tkinter import Toplevel, Label

        def create_tooltip(widget, text):
            tip = None  # Initialisation dans la portée parente

            def enter(event):
                nonlocal tip
                x = widget.winfo_rootx() + 25
                y = widget.winfo_rooty() + 25

                tip = Toplevel(widget)
                tip.wm_overrideredirect(True)
                tip.wm_geometry(f"+{x}+{y}")

                label = Label(tip, text=text, bg="yellow", relief='solid', borderwidth=1)
                label.pack()

            def leave(event):
                nonlocal tip
                if tip and tip.winfo_exists():
                    tip.destroy()
                    tip = None

            widget.bind("<Enter>", enter)
            widget.bind("<Leave>", leave)

        create_tooltip(self.scan_type, "Choisissez le type de scan à effectuer")
        create_tooltip(self.disable_dns_checkbtn, "Désactive la résolution DNS pour plus de rapidité")
        create_tooltip(self.privileged_checkbtn, "Nécessite les droits administrateur pour certains scans")

    def update_scan_info(self, event=None):
        """Met à jour l'info sur le scan sélectionné"""
        scan_type = self.scan_type.get()
        scan_info = self.scanner.current_config['scan_types'].get(scan_type, {})

        info_text = f"{scan_info.get('name', '')}: {scan_info.get('description', '')}"
        self.scan_info.config(text=info_text)

    def start_scan(self):
        """Démarre le scan selon la méthode sélectionnée"""
        # Réinitialisation
        self.stop_scan_flag = False
        self.is_scanning = True
        self.clear_results()
        self.progress.grid(row=3, column=0, columnspan=2, sticky='ew', pady=5)
        self.progress.start()

        # Mise à jour des boutons avant les vérifications
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # Récupération des paramètres
        scan_type = self.scan_type.get()
        self.scanner.current_config['disable_dns'] = self.disable_dns.get()
        self.scanner.current_config['privileged'] = self.privileged.get()

        # Vérification fichier Excel pour l'onglet Excel
        tab = self.notebook.tab(self.notebook.select(), "text")

        if tab == "Depuis Excel":
            if not hasattr(self.controller, 'chemin_equipement') or not self.controller.chemin_equipement:
                messagebox.showwarning(
                    "Fichier requis",
                    "Veuillez d'abord sélectionner un fichier Excel dans la page d'accueil",
                    parent=self
                )
                # Réinitialisation des boutons en cas d'erreur
                self.progress.stop()
                self.progress.grid_forget()
                self.is_scanning = False
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
                self.controller.show_home()
                return

            if not os.path.exists(self.controller.chemin_equipement):
                messagebox.showerror(
                    "Fichier introuvable",
                    "Le fichier Excel spécifié n'existe plus",
                    parent=self
                )
                # Réinitialisation des boutons en cas d'erreur
                self.progress.stop()
                self.progress.grid_forget()
                self.is_scanning = False
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
                return

            self.scanner.set_excel_path(self.controller.chemin_equipement)
            self.scan_thread = threading.Thread(
                target=self.run_excel_scan,
                args=(scan_type,),
                daemon=True
            )

        elif tab == "Plage IP":
            start_ip = self.start_ip.get().strip()
            end_ip = self.end_ip.get().strip()

            if not start_ip or not end_ip:
                messagebox.showwarning(
                    "Erreur",
                    "Veuillez entrer une plage IP valide",
                    parent=self
                )
                # Réinitialisation des boutons en cas d'erreur
                self.progress.stop()
                self.progress.grid_forget()
                self.is_scanning = False
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
                return

            self.scan_thread = threading.Thread(
                target=self.run_ip_range_scan,
                args=(start_ip, end_ip, scan_type),
                daemon=True
            )

        # Si tout est OK, lancer le scan
        self.controller.update_status(f"Scan {scan_type} en cours...")
        self.scan_thread.start()

    def run_excel_scan(self, scan_type):
        """Exécute le scan depuis Excel dans un thread séparé"""
        results = self.scanner.scan_from_excel(scan_type)
        self.display_results(results)

    def run_ip_range_scan(self, start_ip, end_ip, scan_type):
        """Exécute le scan de plage IP dans un thread séparé"""
        results = self.scanner.scan_ip_range(start_ip, end_ip, scan_type)
        self.display_results(results)

    def stop_scan(self):
        """Demande l'arrêt du scan en cours"""
        self.stop_scan_flag = True
        self.is_scanning = False  # Nouvel état
        self.controller.update_status("Arrêt demandé...")

        # Mise à jour des boutons
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def display_results(self, results):
        """Affiche les résultats dans l'interface"""
        self.progress.stop()
        self.progress.grid_forget()
        self.is_scanning = False  # Nouvel état

        # Mise à jour des boutons
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        # Sauvegarde des résultats complets
        self.current_results = results

        # Affichage des erreurs
        if 'error' in results:
            if results.get('action') == 'redirect_home':
                messagebox.showwarning(
                    "Fichier requis",
                    results['error'],
                    parent=self
                )
                self.controller.show_home()
            else:
                messagebox.showerror(
                    "Erreur",
                    results['error'],
                    parent=self
                )
            return

        # Nettoyage de l'arbre
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Tri des résultats: UP d'abord, puis DOWN
        sorted_hosts = sorted(
            results.get('hosts', []),
            key=lambda x: (x.get('status') != 'UP', x.get('ip', ''))
        )

        # Ajout des hôtes
        for host in sorted_hosts:
            status = host.get('status', 'UNKNOWN')
            details = ""

            if status == 'UP' and host.get('scan_type') == 'advanced':
                ports = host.get('ports', [])
                details = f"{len(ports)} ports ouverts"
                if ports:
                    details += f" ({ports[0]['port']}/{ports[0]['protocol']}...)"

            self.tree.insert('', 'end', values=(
                host.get('hostname', ''),
                host.get('ip', ''),
                status,
                details
            ), tags=(status.lower(),))

        # Configuration des tags pour le style
        self.tree.tag_configure('up', background='#e6f7e6')  # Vert clair pour UP
        self.tree.tag_configure('down', background='#ffebee')  # Rouge clair pour DOWN

        # Affichage des erreurs individuelles
        if results.get('errors'):
            error_count = len(results['errors'])
            self.tree.insert('', 'end', values=(
                f"{error_count} erreurs",
                "",
                "ERROR",
                "Voir détails"
            ), tags=('error',))
            self.tree.tag_configure('error', background='#fff3e0')  # Orange clair pour erreurs

        self.controller.update_status(
            f"Scan terminé - {len([h for h in results.get('hosts', []) if h.get('status') == 'UP'])} UP, "
            f"{len([h for h in results.get('hosts', []) if h.get('status') == 'DOWN'])} DOWN"
        )

    def show_details_window(self, event):
        """Affiche les détails dans une fenêtre séparée"""
        selected = self.tree.focus()
        if not selected:
            return

        item = self.tree.item(selected)
        values = item['values']

        # Si c'est une ligne d'erreur
        if 'error' in item['tags']:
            self.show_error_details()
            return

        # Recherche de l'hôte correspondant
        ip = values[1]
        host = next((h for h in self.current_results.get('hosts', []) if h['ip'] == ip), None)
        if not host:
            return

        # Création de la fenêtre de détails
        if self.details_window and self.details_window.winfo_exists():
            self.details_window.destroy()

        self.details_window = tk.Toplevel(self)
        self.details_window.title(f"Détails pour {host.get('hostname', '')} ({ip})")
        self.details_window.geometry("600x400")

        # Zone de texte pour les détails
        text_frame = ttk.Frame(self.details_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        details_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            padx=10,
            pady=10
        )
        details_text.pack(fill=tk.BOTH, expand=True)

        # Remplissage des détails
        details_text.insert(tk.END, f"Détails pour {host.get('hostname', '')} ({ip})\n\n", 'header')
        details_text.tag_config('header', font=('Consolas', 11, 'bold'))

        details_text.insert(tk.END, f"Statut: {host.get('status', 'inconnu')}\n")

        if host.get('os'):
            details_text.insert(tk.END,
                                f"OS probable: {host['os'].get('name', '')} (précision: {host['os'].get('accuracy', '')}%)\n\n")

        if host.get('ports'):
            details_text.insert(tk.END, "Ports ouverts:\n", 'subheader')
            details_text.tag_config('subheader', font=('Consolas', 10, 'bold'))

            for port in host['ports']:
                details_text.insert(tk.END,
                                    f"- {port['port']}/{port['protocol']}: {port['state']}\n"
                                    f"  Service: {port['service']} {port.get('version', '')}\n\n")

        details_text.config(state=tk.DISABLED)

    def show_error_details(self):
        """Affiche les détails des erreurs"""
        if not self.current_results or not self.current_results.get('errors'):
            return

        error_window = tk.Toplevel(self)
        error_window.title("Détails des erreurs")
        error_window.geometry("500x300")

        text_frame = ttk.Frame(error_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        error_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=('Consolas', 9),
            padx=10,
            pady=10
        )
        error_text.pack(fill=tk.BOTH, expand=True)

        error_text.insert(tk.END, "Erreurs rencontrées:\n\n", 'header')
        error_text.tag_config('header', font=('Consolas', 11, 'bold'))
        error_text.tag_config('error', foreground='red')

        for error in self.current_results.get('errors', []):
            error_text.insert(tk.END,
                              f"IP: {error.get('ip', '')}\n"
                              f"Hostname: {error.get('hostname', 'N/A')}\n"
                              f"Erreur: {error.get('error', 'Inconnue')}\n\n", 'error')

        error_text.config(state=tk.DISABLED)

    def export_results(self):
        """Exporte les résultats"""
        if not self.current_results or not self.current_results.get('hosts'):
            messagebox.showwarning(
                "Aucun résultat",
                "Aucun résultat à exporter",
                parent=self
            )
            return

        file = filedialog.asksaveasfilename(
            title="Exporter les résultats",
            defaultextension=".xlsx",
            filetypes=[
                ("Excel", "*.xlsx"),
                ("JSON", "*.json"),
                ("HTML", "*.html"),
                ("Tous", "*.*")
            ],
            parent=self
        )

        if file:
            ext = os.path.splitext(file)[1].lower()
            format_map = {
                '.xlsx': 'excel',
                '.json': 'json',
                '.html': 'html'
            }

            success = self.scanner.export_results(
                self.current_results,
                format_map.get(ext, 'excel'),
                os.path.splitext(file)[0]
            )

            if success:
                messagebox.showinfo(
                    "Succès",
                    f"Résultats exportés vers {file}",
                    parent=self
                )
            else:
                messagebox.showerror(
                    "Erreur",
                    "Échec de l'export",
                    parent=self
                )

    def clear_results(self):
        """Efface les résultats actuels"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.current_results = None

    def update_path_display(self):
        """Met à jour l'affichage du chemin Excel"""
        if hasattr(self.controller, 'chemin_equipement'):
            if self.controller.chemin_equipement:
                self.excel_status.config(
                    text=f"Fichier sélectionné: {os.path.basename(self.controller.chemin_equipement)}",
                    style='TLabel'
                )
            else:
                self.excel_status.config(
                    text="Aucun fichier sélectionné (aller à la page Accueil)",
                    style='Warning.TLabel'
                )

    def on_show(self):
        """Appelé quand la frame est affichée"""
        self.controller.update_status("Prêt pour le scan réseau")
        self.update_path_display()
        self.update_scan_info()


class ModernBackupFrame(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, style='Content.TFrame')
        self.controller = controller
        self.backup_manager = BackupManager()
        self.current_device = None
        self.stop_backup_flag = False
        self.messages_shown = False

        # Variables d'interface
        self.sftp_host = tk.StringVar(value="192.168.179.30")
        self.sftp_port = tk.StringVar(value="22")
        self.sftp_user = tk.StringVar(value="user")
        self.sftp_pass = tk.StringVar()
        self.sftp_path = tk.StringVar(value="/backups3")
        self.sftp_enabled = tk.BooleanVar(value=False)

        # Configuration de l'interface
        self.setup_ui()

    def setup_ui(self):
        """Configure l'interface utilisateur moderne"""
        container = ttk.Frame(self, style='Content.TFrame')
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header avec style similaire aux autres pages
        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(header,
                  text="💾 Backup Automatisé",
                  style='Title.TLabel',
                  font=('Segoe UI', 18, 'bold')).pack(side=tk.LEFT)

        # Section aide
        help_frame = ttk.LabelFrame(container, text="Aide & Explications", style='Card.TFrame')
        help_frame.pack(fill=tk.X, pady=(0, 10))

        help_text = """
        Cette page permet de sauvegarder les configurations des équipements réseau.
        Sélectionnez un dossier de backup local et configurez un serveur SFTP distant s'il existe.
        """
        ttk.Label(help_frame, text=help_text, style='TLabel').pack(padx=5, pady=5, anchor='w')

        # Configuration en deux colonnes
        config_frame = ttk.Frame(container, style='Card.TFrame')
        config_frame.pack(fill=tk.X, pady=10)

        # Colonne gauche - Backup local
        local_col = ttk.Frame(config_frame, style='Card.TFrame')
        local_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        ttk.Label(local_col, text="Dossier Backup Local:", style='TLabel').pack(anchor=tk.W)

        self.local_path_label = ttk.Label(local_col,
                                          text="Non sélectionné",
                                          style='TLabel',
                                          font=('Segoe UI', 10))
        self.local_path_label.pack(anchor=tk.W, padx=5, pady=5)

        btn_frame = ttk.Frame(local_col, style='Card.TFrame')
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame,
                   text="📂 Sélectionner Dossier",
                   command=self.select_backup_folder,
                   style='Primary.TButton').pack(side=tk.LEFT)

        # Colonne droite - Configuration SFTP
        # Colonne droite - Configuration SFTP
        sftp_col = ttk.Frame(config_frame, style='Card.TFrame')
        sftp_col.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5)

        ttk.Label(sftp_col, text="Configuration SFTP:", style='TLabel').pack(anchor=tk.W)

        # Remplacer la partie grid par pack :
        entries = [
            ("Serveur:", "sftp_host", 25),
            ("Port:", "sftp_port", 5),
            ("Utilisateur:", "sftp_user", 15),
            ("Mot de passe:", "sftp_pass", 15, True),
            ("Chemin:", "sftp_path", 25)
        ]

        for label, var, width, *is_password in entries:
            row = ttk.Frame(sftp_col, style='Card.TFrame')
            row.pack(fill=tk.X, pady=2)  # Changé de grid à pack

            ttk.Label(row, text=label, style='TLabel').pack(side=tk.LEFT, padx=5)

            entry = ttk.Entry(row,
                              textvariable=getattr(self, var),
                              width=width,
                              show="*" if is_password else None)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Boutons SFTP - également modifié pour utiliser pack
        sftp_btn_frame = ttk.Frame(sftp_col, style='Card.TFrame')
        sftp_btn_frame.pack(fill=tk.X, pady=5)  # Changé de grid à pack

        ttk.Button(sftp_btn_frame,
                   text="🔍 Tester Connexion",
                   command=self.test_sftp_connection,
                   style='Info.TButton').pack(side=tk.LEFT, padx=2)

        ttk.Checkbutton(sftp_btn_frame,
                        text="Activer SFTP",
                        variable=self.sftp_enabled,
                        style='Switch.TCheckbutton').pack(side=tk.LEFT, padx=2)

        # Barre de boutons d'action
        action_frame = ttk.Frame(container, style='Card.TFrame')
        action_frame.pack(fill=tk.X, pady=10)

        self.start_btn = ttk.Button(action_frame,
                                    text="▶ Démarrer Backup",
                                    command=self.start_backup,
                                    style='Accent.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(action_frame,
                                   text="⏹ Arrêter",
                                   command=self.stop_backup,
                                   style='Danger.TButton',
                                   state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(action_frame,
                   text="🗑 Effacer Journal",
                   command=self.clear_logs,
                   style='Toolbutton').pack(side=tk.LEFT, padx=5)

        ttk.Button(action_frame,
                   text="📤 Exporter Logs",
                   command=self.export_logs,
                   style='Toolbutton').pack(side=tk.RIGHT, padx=5)

        # Section résultats avec onglets
        self.notebook = ttk.Notebook(container, style='Custom.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        # Onglet Journal
        log_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(log_tab, text="📝 Journal d'activité")

        self.log_text = scrolledtext.ScrolledText(
            log_tab,
            wrap=tk.WORD,
            font=('Consolas', 10),
            padx=10,
            pady=10,
            background='#f8f9fa',
            relief=tk.FLAT,
            state='disabled'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Onglet Statistiques
        stats_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(stats_tab, text="📊 Statistiques")

        self.setup_stats_section(stats_tab)

        # Barre de progression
        self.progress = ttk.Progressbar(log_tab,
                                        mode='indeterminate',
                                        style='Custom.Horizontal.TProgressbar')

        # Configuration des tags pour le texte coloré
        for tag, color in [
            ('success', '#28a745'),
            ('error', '#dc3545'),
            ('warning', '#ffc107'),
            ('info', '#17a2b8'),
            ('device', '#007bff'),
            ('command', '#6f42c1')
        ]:
            self.log_text.tag_config(tag, foreground=color)

        # Initialisation
        self.update_path_display()

    def setup_stats_section(self, parent):
        """Configure la section statistiques"""
        stats_frame = ttk.Frame(parent, style='Card.TFrame')
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Métriques principales
        metrics_frame = ttk.Frame(stats_frame, style='Card.TFrame')
        metrics_frame.pack(fill=tk.X, pady=10)

        metrics = [
            ("Sauvegardes réussies:", "0", "success"),
            ("Échecs:", "0", "error"),
            ("En cours:", "0", "info"),
            ("Dernière sauvegarde:", "-", "info"),
            ("Taille totale:", "-", "info")
        ]

        for i, (label, value, style) in enumerate(metrics):
            frame = ttk.Frame(metrics_frame, style='Card.TFrame')
            frame.grid(row=i // 2, column=i % 2, sticky='ew', padx=5, pady=5)

            ttk.Label(frame, text=label, style='TLabel').pack(side=tk.LEFT)
            ttk.Label(frame, text=value, style=f'{style}.TLabel',
                      font=('Segoe UI', 10, 'bold')).pack(side=tk.RIGHT)
            setattr(self, f'stat_{label.split(":")[0].lower().replace(" ", "_")}', frame.children['!label2'])

        # Graphique simple (simulé)
        self.graph_canvas = tk.Canvas(stats_frame,
                                      height=120,
                                      bg='white',
                                      highlightthickness=0)
        self.graph_canvas.pack(fill=tk.X, pady=10)
        self.draw_placeholder_graph()

        # Liste des derniers backups
        ttk.Label(stats_frame,
                  text="Dernières sauvegardes:",
                  style='TLabel').pack(anchor=tk.W, pady=5)

        self.last_backups_list = tk.Listbox(stats_frame,
                                            height=4,
                                            font=('Segoe UI', 9),
                                            bg='white',
                                            relief=tk.FLAT)
        self.last_backups_list.pack(fill=tk.X)

    def draw_placeholder_graph(self):
        """Dessine un graphique placeholder"""
        w = self.graph_canvas.winfo_width() or 400
        h = self.graph_canvas.winfo_height() or 120

        self.graph_canvas.delete('all')

        # Axes
        self.graph_canvas.create_line(30, h - 30, w - 30, h - 30, fill='#666')  # X
        self.graph_canvas.create_line(30, 20, 30, h - 30, fill='#666')  # Y

        # Étiquettes
        self.graph_canvas.create_text(15, h // 2, text="Sauvegardes", angle=90, fill='#666')
        self.graph_canvas.create_text(w // 2, h - 15, text="Jours", fill='#666')

        # Données simulées (histogramme)
        data = [30, 50, 80, 65]
        colors = ['#3b82f6', '#3b82f6', '#10b981', '#3b82f6']
        bar_width = 40
        spacing = 30

        for i, value in enumerate(data):
            x0 = 50 + i * (bar_width + spacing)
            x1 = x0 + bar_width
            y0 = h - 30
            y1 = y0 - value

            self.graph_canvas.create_rectangle(x0, y0, x1, y1, fill=colors[i], outline='')

    def select_backup_folder(self):
        """Sélectionne le dossier backup principal"""
        path = filedialog.askdirectory(title="Sélectionner le dossier BACKUP PRINCIPAL")
        if path:
            self.controller.set_chemin_backup(path)
            self.local_path_label.config(text=f"Dossier sélectionné: {path}")
            self.log_message(f"📁 Dossier backup sélectionné: {path}", 'info')

    def test_sftp_connection(self):
        """Teste la connexion SFTP"""
        self.backup_manager.sftp.configure(
            host=self.sftp_host.get(),
            port=int(self.sftp_port.get()),
            username=self.sftp_user.get(),
            password=self.sftp_pass.get(),
            remote_path=self.sftp_path.get()
        )

        success, message = self.backup_manager.sftp.test_connection()
        if success:
            self.log_message(f"✅ Test SFTP réussi: {message}", 'success')
            messagebox.showinfo("Test SFTP", message, parent=self)
        else:
            self.log_message(f"❌ Échec test SFTP: {message}", 'error')
            messagebox.showerror("Test SFTP", message, parent=self)

    def start_backup(self):
        """Démarre le processus de sauvegarde"""
        # Vérification fichier Excel
        if not hasattr(self.controller, 'chemin_equipement') or not self.controller.chemin_equipement:
            messagebox.showwarning(
                "Fichier requis",
                "Veuillez d'abord sélectionner un fichier Excel dans la page d'accueil"
            )
            self.controller.show_home()
            return

        # Vérification dossier backup
        if not hasattr(self.controller, 'chemin_backup') or not self.controller.chemin_backup:
            messagebox.showwarning("Erreur", "Veuillez sélectionner un dossier backup principal")
            return

        # Demande des identifiants
        username = simpledialog.askstring("Authentification", "Nom d'utilisateur SSH:")
        if not username: return

        password = simpledialog.askstring("Authentification", "Mot de passe SSH:", show='*')
        if not password: return

        # Configuration SFTP si activé
        if self.sftp_enabled.get():
            self.backup_manager.sftp.configure(
                host=self.sftp_host.get(),
                port=int(self.sftp_port.get()),
                username=self.sftp_user.get(),
                password=self.sftp_pass.get(),
                remote_path=self.sftp_path.get()
            )
            self.log_message("⚙️ Transfert SFTP activé", 'info')

        # Préparation de l'interface
        self.clear_logs()
        self.progress.pack(fill=tk.X, pady=5)
        self.progress.start()
        self.stop_backup_flag = False
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.stat_en_cours.config(text="1")

        # Lancement dans un thread séparé
        threading.Thread(
            target=self.execute_backup,
            args=(username, password),
            daemon=True
        ).start()

    def execute_backup(self, username, password):
        """Exécute le backup avec affichage en temps réel"""
        try:
            # Création du dossier de session
            session_path = self.backup_manager.create_session_folder(self.controller.chemin_backup)
            self.log_message(f"📂 Session de backup créée: {session_path}", 'info')

            # Lecture des équipements
            df = pd.read_excel(self.controller.chemin_equipement, header=2)
            devices = df[df["Device Type"] == "cisco_ios"].to_dict('records')
            total_devices = len(devices)

            if not devices:
                self.log_message("⚠️ Aucun équipement Cisco à sauvegarder", 'warning')
                return

            # Réinitialisation des statistiques
            self.stat_sauvegardes_réussies.config(text="0")
            self.stat_échecs.config(text="0")

            success_count = 0
            fail_count = 0

            # Sauvegarde des équipements
            for idx, device in enumerate(devices, 1):
                if self.stop_backup_flag:
                    break

                self.current_device = device
                self.stat_en_cours.config(text=f"{idx}/{total_devices}")

                hostname = device.get('Hostname', 'inconnu')
                ip = device.get('IP Address', '')
                self.log_message(f"\n🔌 Traitement de {hostname} ({ip})...", 'device')

                # Exécution de la sauvegarde
                status, message = self.backup_manager.backup_device(device, username, password, session_path)

                if status:
                    success_count += 1
                    self.stat_sauvegardes_réussies.config(text=str(success_count))
                    self.log_message(message, 'success')

                    # Transfert SFTP si activé
                    if self.sftp_enabled.get() and not self.stop_backup_flag:
                        backup_file = os.path.join(session_path, f"{hostname}.cfg")
                        if os.path.exists(backup_file):
                            sftp_status, sftp_msg = self.backup_manager.sftp.upload_backup(backup_file)
                            if sftp_status:
                                self.log_message(f"☁️ {sftp_msg}", 'info')
                            else:
                                self.log_message(f"⚠️ SFTP: {sftp_msg}", 'warning')
                        else:
                            self.log_message("⚠️ Fichier de backup local introuvable pour SFTP", 'warning')
                else:
                    fail_count += 1
                    self.stat_échecs.config(text=str(fail_count))
                    self.log_message(message, 'error')

            # Mise à jour finale
            if not self.stop_backup_flag:
                total_size = self.calculate_folder_size(session_path)
                self.stat_taille_totale.config(text=f"{total_size} MB")
                self.stat_dernière_sauvegarde.config(text=datetime.now().strftime("%d/%m/%Y %H:%M"))
                self.update_last_backups_list(session_path)

                self.log_message(f"\n📊 Résumé: {success_count} succès, {fail_count} échecs", 'info')
                self.log_message(f"💾 Taille totale: {total_size} MB", 'info')

        except Exception as e:
            self.log_message(f"❌ Erreur critique: {str(e)}", 'error')
        finally:
            self.progress.stop()
            self.progress.pack_forget()
            self.current_device = None
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.stat_en_cours.config(text="0")
            self.controller.update_status("Sauvegarde terminée")

    def calculate_folder_size(self, folder_path):
        """Calcule la taille d'un dossier en MB"""
        total_size = 0
        for dirpath, _, filenames in os.walk(folder_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return round(total_size / (1024 * 1024), 2)  # Convertir en MB

    def update_last_backups_list(self, session_path):
        """Met à jour la liste des derniers backups"""
        self.last_backups_list.delete(0, tk.END)

        # Récupérer les 4 derniers dossiers de backup
        backup_root = self.controller.chemin_backup
        if not os.path.exists(backup_root):
            return

        backups = sorted([d for d in os.listdir(backup_root)
                          if os.path.isdir(os.path.join(backup_root, d))],
                         reverse=True)[:4]

        for backup in backups:
            size = self.calculate_folder_size(os.path.join(backup_root, backup))
            self.last_backups_list.insert(tk.END, f"{backup} - {size} MB")

    def stop_backup(self):
        """Arrête le backup en cours"""
        self.stop_backup_flag = True
        if self.current_device:
            hostname = self.current_device.get("Hostname", "Inconnu")
            ip = self.current_device.get("IP Address", "0.0.0.0")
            self.log_message(f"⏹️ Sauvegarde arrêtée pour {hostname} ({ip})", 'warning')
        self.controller.update_status("Sauvegarde arrêtée")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.stat_en_cours.config(text="0")

    def clear_logs(self):
        """Efface les logs"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.NORMAL)
        self.current_device = None
        self.controller.update_status("Journal effacé")

    def log_message(self, message, tag=None):
        """Ajoute un message au journal"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.NORMAL)

    def export_logs(self):
        """Exporte les logs vers un fichier texte"""
        if not self.log_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Aucun contenu", "Le journal est vide, rien à exporter")
            return

        file_path = filedialog.asksaveasfilename(
            title="Exporter les logs",
            defaultextension=".txt",
            filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")]
        )

        if file_path:
            try:
                content = self.log_text.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.log_message(f"✅ Logs exportés vers {file_path}", 'success')
                messagebox.showinfo("Succès", "Exportation des logs terminée")
            except Exception as e:
                self.log_message(f"❌ Erreur lors de l'export: {str(e)}", 'error')
                messagebox.showerror("Erreur", f"Échec de l'export: {str(e)}")

    def update_path_display(self):
        """Met à jour l'affichage des chemins"""
        if hasattr(self.controller, 'chemin_backup') and self.controller.chemin_backup:
            self.local_path_label.config(text=f"Dossier sélectionné: {self.controller.chemin_backup}")

    def on_show(self):
        """Exécuté lorsque la page est affichée"""
        self.controller.update_status("Page de backup - Prêt")
        self.update_path_display()


    def create_form_field(self, parent, label, var, width=None, is_password=False):
        frame = ttk.Frame(parent, style='Card.TFrame')
        frame.pack(fill=tk.X, pady=2)

        ttk.Label(frame, text=label, style='TLabel').pack(side=tk.LEFT, padx=5)

        entry = ttk.Entry(frame, textvariable=var, width=width, show="*" if is_password else None)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        return entry



class ModernConfigFrame(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, style='Content.TFrame')
        self.controller = controller
        self.current_device = None
        self.stop_configuration_flag = False
        self.messages_shown = False

        # Variables d'interface
        self.config_path = tk.StringVar()
        self.scope_var = tk.StringVar(value="Y")
        self.device_filter_var = tk.StringVar(value="Tous")

        # Configuration de l'interface
        self.setup_ui()

    def setup_ui(self):
        """Configure l'interface utilisateur moderne inspirée de la page scan"""
        container = ttk.Frame(self, style='Content.TFrame')
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header avec style similaire à la page scan
        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(header,
                  text="⚙️ Configuration des Équipements",
                  style='Title.TLabel',
                  font=('Segoe UI', 18, 'bold')).pack(side=tk.LEFT)

        # Section aide
        help_frame = ttk.LabelFrame(container, text="Aide & Explications", style='Card.TFrame')
        help_frame.pack(fill=tk.X, pady=(0, 10))

        help_text = """
        Cette page permet d'appliquer des configurations aux équipements réseau.
        Sélectionnez un fichier de configuration et choisissez les équipements cibles.
        """
        ttk.Label(help_frame, text=help_text, style='TLabel').pack(padx=5, pady=5, anchor='w')

        # Section configuration en deux colonnes
        config_frame = ttk.Frame(container, style='Card.TFrame')
        config_frame.pack(fill=tk.X, pady=10)

        # Colonne gauche - Fichier de configuration
        left_col = ttk.Frame(config_frame, style='Card.TFrame')
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        ttk.Label(left_col, text="Fichier de configuration:", style='TLabel').pack(anchor=tk.W)

        file_frame = ttk.Frame(left_col, style='Card.TFrame')
        file_frame.pack(fill=tk.X, pady=5)

        self.config_entry = ttk.Entry(file_frame, textvariable=self.config_path, width=40)
        self.config_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Button(file_frame, text="Parcourir",
                   command=self.select_config_file,
                   style='Primary.TButton').pack(side=tk.RIGHT)

        # Colonne droite - Options de scope
        right_col = ttk.Frame(config_frame, style='Card.TFrame')
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5)

        ttk.Label(right_col, text="Filtrer les équipements:", style='TLabel').pack(anchor=tk.W)

        # Options sous forme de boutons radio avec style moderne
        scope_frame = ttk.Frame(right_col, style='Card.TFrame')
        scope_frame.pack(fill=tk.X, pady=5)

        ttk.Radiobutton(scope_frame, text="Équipements marqués 'Y'",
                        variable=self.scope_var, value="Y",
                        style='Toolbutton').pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(scope_frame, text="Tous les équipements",
                        variable=self.scope_var, value="all",
                        style='Toolbutton').pack(side=tk.LEFT, padx=5)

        # Barre de boutons d'action avec style moderne
        btn_frame = ttk.Frame(container, style='Card.TFrame')
        btn_frame.pack(fill=tk.X, pady=10)

        self.start_btn = ttk.Button(btn_frame,
                                    text="▶ Démarrer Configuration",
                                    command=self.start_configuration,
                                    style='Accent.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame,
                                   text="⏹ Arrêter",
                                   command=self.stop_configuration,
                                   style='Danger.TButton',
                                   state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame,
                   text="🗑 Effacer Journal",
                   command=self.clear_logs,
                   style='Toolbutton').pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame,
                   text="📤 Exporter Logs",
                   command=self.export_logs,
                   style='Toolbutton').pack(side=tk.RIGHT, padx=5)

        # Section résultats avec onglets comme dans la page scan
        self.notebook = ttk.Notebook(container, style='Custom.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        # Onglet Journal
        log_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(log_tab, text="📝 Journal d'exécution")

        self.log_text = scrolledtext.ScrolledText(
            log_tab,
            width=100,
            height=25,
            wrap=tk.WORD,
            font=('Consolas', 10),
            padx=10,
            pady=10,
            background='#f8f9fa',
            relief=tk.FLAT,
            state='disabled'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Onglet Statistiques
        stats_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(stats_tab, text="📊 Statistiques")

        self.setup_stats_section(stats_tab)

        # Barre de progression
        self.progress = ttk.Progressbar(log_tab,
                                        mode='indeterminate',
                                        style='Custom.Horizontal.TProgressbar')

        # Configuration des tags pour le texte coloré
        for tag, color in [
            ('success', '#28a745'),
            ('error', '#dc3545'),
            ('warning', '#ffc107'),
            ('info', '#17a2b8'),
            ('device', '#007bff'),
            ('command', '#6f42c1')
        ]:
            self.log_text.tag_config(tag, foreground=color)

        # Initialisation
        self.update_path_display()

    def setup_stats_section(self, parent):
        """Configure la section statistiques avec des indicateurs visuels"""
        stats_frame = ttk.Frame(parent, style='Card.TFrame')
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Métriques principales
        metrics_frame = ttk.Frame(stats_frame, style='Card.TFrame')
        metrics_frame.pack(fill=tk.X, pady=10)

        metrics = [
            ("Équipements configurés:", "0", "success"),
            ("Échecs:", "0", "error"),
            ("En cours:", "0", "info"),
            ("Dernière session:", "-", "info")
        ]

        for i, (label, value, style) in enumerate(metrics):
            frame = ttk.Frame(metrics_frame, style='Card.TFrame')
            frame.grid(row=i // 2, column=i % 2, sticky='ew', padx=5, pady=5)

            ttk.Label(frame, text=label, style='TLabel').pack(side=tk.LEFT)
            ttk.Label(frame, text=value, style=f'{style}.TLabel',
                      font=('Segoe UI', 10, 'bold')).pack(side=tk.RIGHT)
            setattr(self, f'stat_{label.split(":")[0].lower().replace(" ", "_")}', frame.children['!label2'])

        # Graphique simple (simulé)
        self.graph_canvas = tk.Canvas(stats_frame,
                                      height=120,
                                      bg='white',
                                      highlightthickness=0)
        self.graph_canvas.pack(fill=tk.X, pady=10)
        self.draw_placeholder_graph()

        # Légende
        legend_frame = ttk.Frame(stats_frame, style='Card.TFrame')
        legend_frame.pack(fill=tk.X)

        ttk.Label(legend_frame,
                  text="Historique des configurations:",
                  style='TLabel').pack(anchor=tk.W)

    def draw_placeholder_graph(self):
        """Dessine un graphique placeholder"""
        w = self.graph_canvas.winfo_width() or 400
        h = self.graph_canvas.winfo_height() or 120

        self.graph_canvas.delete('all')

        # Axes
        self.graph_canvas.create_line(30, h - 30, w - 30, h - 30, fill='#666')  # X
        self.graph_canvas.create_line(30, 20, 30, h - 30, fill='#666')  # Y

        # Étiquettes
        self.graph_canvas.create_text(15, h // 2, text="Équipements", angle=90, fill='#666')
        self.graph_canvas.create_text(w // 2, h - 15, text="Temps", fill='#666')

        # Données simulées
        points = [(50, 80), (150, 40), (250, 90), (350, 60)]
        for i, (x, y) in enumerate(points):
            self.graph_canvas.create_oval(x - 3, h - y - 3, x + 3, h - y + 3, fill='#3b82f6')
            if i > 0:
                px, py = points[i - 1]
                self.graph_canvas.create_line(px, h - py, x, h - y, fill='#3b82f6', width=2)

    def select_config_file(self):
        """Sélectionne le fichier de configuration"""
        fichier = filedialog.askopenfilename(
            title="Sélectionner le fichier de configuration",
            filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")]
        )
        if fichier:
            self.controller.set_chemin_config(fichier)
            self.log_message(f"✅ Fichier de configuration sélectionné: {os.path.basename(fichier)}", 'success')
            self.messages_shown = False

    def update_path_display(self):
        """Met à jour l'affichage des chemins"""
        if hasattr(self.controller, 'chemin_configurations') and self.controller.chemin_configurations:
            self.config_path.set(self.controller.chemin_configurations)

    def clear_logs(self):
        """Efface les logs"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.NORMAL)
        self.current_device = None
        self.controller.update_status("Journal effacé")
        self.messages_shown = False

    def log_message(self, message, tag=None):
        """Ajoute un message aux logs"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.NORMAL)

    def start_configuration(self):
        """Démarre la configuration après vérification"""
        # Vérification fichier Excel
        if not hasattr(self.controller, 'chemin_equipement') or not self.controller.chemin_equipement:
            messagebox.showwarning(
                "Fichier requis",
                "Veuillez d'abord sélectionner un fichier Excel dans la page d'accueil"
            )
            self.controller.show_home()
            return

        # Vérification fichier de configuration
        if not hasattr(self.controller, 'chemin_configurations') or not self.controller.chemin_configurations:
            self.log_message("❌ Erreur: Fichier de configuration requis", 'error')
            messagebox.showwarning("Configuration impossible",
                                   "Veuillez sélectionner un fichier de configuration")
            return

        username = simpledialog.askstring("Authentification", "Nom d'utilisateur SSH:")
        if not username: return

        password = simpledialog.askstring("Authentification", "Mot de passe SSH:", show='*')
        if not password: return

        enable_password = simpledialog.askstring("Authentification",
                                                 "Mot de passe Enable (laisser vide si identique):",
                                                 show='*')
        enable_password = enable_password if enable_password else password

        # Mise à jour de l'interface
        self.clear_logs()
        self.progress.pack(fill=tk.X, pady=5)
        self.progress.start()
        self.stop_configuration_flag = False
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.stat_en_cours.config(text="1")

        # Lecture des commandes
        with open(self.controller.chemin_configurations, 'r') as f:
            commands = [cmd.strip() for cmd in f if cmd.strip() and not cmd.startswith('#')]

        if not commands:
            self.log_message("⚠️ Avertissement: Aucune commande valide dans le fichier", 'warning')
            return

        # Lancement dans un thread séparé
        threading.Thread(
            target=self.execute_configuration,
            args=(username, password, enable_password, commands),
            daemon=True
        ).start()

    def stop_configuration(self):
        """Arrête la configuration en cours"""
        self.stop_configuration_flag = True
        if self.current_device:
            hostname = self.current_device.get("Hostname", "Inconnu")
            ip = self.current_device.get("IP Address", "0.0.0.0")
            self.log_message(f"⏹️ Configuration arrêtée pour {hostname} ({ip})", 'warning')
        self.controller.update_status("Configuration arrêtée")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.stat_en_cours.config(text="0")

    def execute_configuration(self, username, password, enable_password, commands):
        """Exécute la configuration sur les équipements"""
        try:
            # Lecture des équipements
            devices = pd.read_excel(self.controller.chemin_equipement, header=2)
            if self.scope_var.get() == "Y":
                devices = devices[devices["Configurer"] == "Y"]

            devices = devices[devices["Device Type"] == "cisco_ios"]
            total_devices = len(devices)

            if devices.empty:
                self.log_message("⚠️ Avertissement: Aucun équipement à configurer", 'warning')
                return

            # Mise à jour des statistiques
            self.stat_équipements_configurés.config(text="0")
            self.stat_échecs.config(text="0")

            success_count = 0
            fail_count = 0

            # Configuration des équipements
            for idx, device in devices.iterrows():
                if self.stop_configuration_flag:
                    break

                self.current_device = device
                self.stat_en_cours.config(text=f"{idx + 1}/{total_devices}")

                if self.configure_device(device, username, password, enable_password, commands):
                    success_count += 1
                else:
                    fail_count += 1

                # Mise à jour en temps réel des statistiques
                self.stat_équipements_configurés.config(text=str(success_count))
                self.stat_échecs.config(text=str(fail_count))

            if not self.stop_configuration_flag:
                self.log_message(f"\n✅ Succès: Configuration terminée ({success_count} succès, {fail_count} échecs)",
                                 'success')
                self.stat_dernière_session.config(text=datetime.now().strftime("%d/%m/%Y %H:%M"))

        except Exception as e:
            self.log_message(f"❌ Erreur: {str(e)}", 'error')
        finally:
            self.progress.stop()
            self.progress.pack_forget()
            self.current_device = None
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.stat_en_cours.config(text="0")
            self.controller.update_status("Opération terminée")

    def configure_device(self, device, username, password, enable_password, commands):
        """Configure un équipement spécifique"""
        try:
            hostname = device.get("Hostname", "Inconnu")
            ip = device.get("IP Address", "0.0.0.0")

            self.log_message(f"\n[🖥️ {hostname} ({ip})]", 'device')
            self.log_message("🔌 Connexion en cours...")

            # Paramètres de connexion
            device_params = {
                'device_type': 'cisco_ios',
                'host': ip,
                'username': username,
                'password': password,
                'secret': enable_password,
                'timeout': 30,
                'global_delay_factor': 2
            }

            with ConnectHandler(**device_params) as conn:
                conn.enable()
                prompt = conn.find_prompt().strip()
                self.log_message(f"✅ Connecté ({prompt})", 'success')

                # Nouvelle approche: regrouper les commandes par contexte
                config_blocks = []
                current_block = []

                for cmd in commands:
                    cmd = cmd.strip()
                    if not cmd:
                        continue

                    # Si la commande commence par "interface", "router", etc., c'est un nouveau bloc
                    if cmd.lower().startswith(('interface ', 'router ', 'ip route ', 'ip access-list ')):
                        if current_block:  # Sauvegarder le bloc précédent
                            config_blocks.append(current_block)
                        current_block = [cmd]  # Commencer un nouveau bloc
                    else:
                        current_block.append(cmd)  # Ajouter au bloc actuel

                # Ajouter le dernier bloc
                if current_block:
                    config_blocks.append(current_block)

                # Application des blocs de configuration
                self.log_message("⚙️ Application de la configuration...")
                for block in config_blocks:
                    if self.stop_configuration_flag:
                        break

                    # Afficher toutes les commandes du bloc
                    self.log_message(f"# Configuration bloc:", 'command')
                    for cmd in block:
                        self.log_message(f"$ {cmd}", 'command')

                    try:
                        # Envoyer tout le bloc en une fois
                        output = conn.send_config_set(block)

                        if '% Invalid' in output or '% Ambiguous' in output:
                            raise ValueError(f"Erreur dans le bloc de commandes:\n{output}")
                        self.log_message(output)
                    except Exception as cmd_error:
                        self.log_message(f"⚠️ Avertissement: {str(cmd_error)}", 'warning')
                        continue

                # Sauvegarde si non arrêté
                if not self.stop_configuration_flag:
                    self.log_message("💾 Sauvegarde de la configuration...")
                    save_output = conn.send_command_timing('write memory', delay_factor=2)
                    self.log_message(save_output, 'success')
                    self.log_message("✅ Configuration appliquée avec succès", 'success')
                    return True

        except NetmikoTimeoutException:
            self.log_message("❌ Erreur: Timeout de connexion", 'error')
        except NetmikoAuthenticationException:
            self.log_message("❌ Erreur: Authentification échouée", 'error')
        except Exception as e:
            self.log_message(f"❌ Erreur: {str(e)}", 'error')

        return False

    def export_logs(self):
        """Exporte les logs vers un fichier texte"""
        if not self.log_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Aucun contenu", "Le journal est vide, rien à exporter")
            return

        file_path = filedialog.asksaveasfilename(
            title="Exporter les logs",
            defaultextension=".txt",
            filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")]
        )

        if file_path:
            try:
                content = self.log_text.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.log_message(f"✅ Logs exportés vers {file_path}", 'success')
                messagebox.showinfo("Succès", "Exportation des logs terminée")
            except Exception as e:
                self.log_message(f"❌ Erreur lors de l'export: {str(e)}", 'error')
                messagebox.showerror("Erreur", f"Échec de l'export: {str(e)}")

    def on_show(self):
        """Exécuté lorsque la page est affichée"""
        self.controller.update_status("Page de configuration - Prêt")
        self.update_path_display()




class ModernCheckFrame(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, style='Content.TFrame')
        self.controller = controller
        self.current_device = None
        self.stop_verification_flag = False
        self.messages_shown = False
        self.result_queue = queue.Queue()
        self.manual_ips = None

        # Variables d'interface
        self.device_filter_var = tk.StringVar(value="Tous")
        self.ip_range_var = tk.StringVar()

        # Configuration de l'interface
        self.setup_ui()

    def setup_ui(self):
        """Configure l'interface utilisateur moderne"""
        container = ttk.Frame(self, style='Content.TFrame')
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header avec style cohérent
        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(header,
                  text="✅ Vérification de Commandes",
                  style='Title.TLabel',
                  font=('Segoe UI', 18, 'bold')).pack(side=tk.LEFT)

        # Section aide
        help_frame = ttk.LabelFrame(container, text="Aide & Explications", style='Card.TFrame')
        help_frame.pack(fill=tk.X, pady=(0, 10))

        help_text = """
        Cette page permet de vérifier la présence de commandes spécifiques 
        dans la configuration des équipements réseau.
        Entrez les commandes à vérifier et sélectionnez les équipements cibles.
        """
        ttk.Label(help_frame, text=help_text, style='TLabel').pack(padx=5, pady=5, anchor='w')

        # Configuration en deux colonnes
        config_frame = ttk.Frame(container, style='Card.TFrame')
        config_frame.pack(fill=tk.X, pady=10)

        # Colonne gauche - Commandes à vérifier
        left_col = ttk.Frame(config_frame, style='Card.TFrame')
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        ttk.Label(left_col, text="Commandes à vérifier (une par ligne):", style='TLabel').pack(anchor=tk.W)

        self.commands_text = scrolledtext.ScrolledText(
            left_col,
            width=40,
            height=10,
            wrap=tk.WORD,
            font=('Consolas', 10),
            padx=10,
            pady=10,
            background='#f8f9fa',
            relief=tk.FLAT
        )
        self.commands_text.pack(fill=tk.BOTH, expand=True)

        # Colonne droite - Options de ciblage
        right_col = ttk.Frame(config_frame, style='Card.TFrame')
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5)

        # Onglets pour les méthodes de sélection
        self.notebook = ttk.Notebook(right_col, style='Custom.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Onglet Excel
        excel_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(excel_tab, text="Depuis Excel")

        ttk.Label(excel_tab, text="Utilise le fichier Excel défini dans la page Accueil").pack(pady=5)

        self.excel_status = ttk.Label(excel_tab,
                                      text="Aucun fichier sélectionné",
                                      style='TLabel',
                                      font=('Segoe UI', 9))
        self.excel_status.pack(pady=5)

        # Onglet Plage IP
        range_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(range_tab, text="Plage IP")

        ttk.Label(range_tab, text="IP Début:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.start_ip = ttk.Entry(range_tab, width=15)
        self.start_ip.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(range_tab, text="IP Fin:").grid(row=0, column=2, padx=5, pady=5, sticky='e')
        self.end_ip = ttk.Entry(range_tab, width=15)
        self.end_ip.grid(row=0, column=3, padx=5, pady=5)

        # Onglet IPs spécifiques
        specific_tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(specific_tab, text="IPs spécifiques")

        ttk.Label(specific_tab, text="Liste d'IPs (séparées par des virgules):").pack(pady=5)
        self.specific_ips_entry = ttk.Entry(specific_tab)
        self.specific_ips_entry.pack(fill=tk.X, padx=5, pady=5)

        # Barre de boutons d'action
        action_frame = ttk.Frame(container, style='Card.TFrame')
        action_frame.pack(fill=tk.X, pady=10)

        self.start_btn = ttk.Button(action_frame,
                                    text="▶ Démarrer Vérification",
                                    command=self.start_verification,
                                    style='Accent.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(action_frame,
                                   text="⏹ Arrêter",
                                   command=self.stop_verification,
                                   style='Danger.TButton',
                                   state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(action_frame,
                   text="🗑 Effacer Résultats",
                   command=self.clear_results,
                   style='Toolbutton').pack(side=tk.LEFT, padx=5)

        ttk.Button(action_frame,
                   text="📤 Exporter Résultats",
                   command=self.export_results,
                   style='Toolbutton').pack(side=tk.RIGHT, padx=5)

        # Section résultats avec onglets
        results_notebook = ttk.Notebook(container, style='Custom.TNotebook')
        results_notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        # Onglet Résultats
        results_tab = ttk.Frame(results_notebook, style='Card.TFrame')
        results_notebook.add(results_tab, text="📋 Résultats")

        self.result_text = scrolledtext.ScrolledText(
            results_tab,
            wrap=tk.WORD,
            font=('Consolas', 10),
            padx=10,
            pady=10,
            background='#f8f9fa',
            relief=tk.FLAT,
            state='disabled'
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # Onglet Statistiques
        stats_tab = ttk.Frame(results_notebook, style='Card.TFrame')
        results_notebook.add(stats_tab, text="📊 Statistiques")

        self.setup_stats_section(stats_tab)

        # Barre de progression
        self.progress = ttk.Progressbar(results_tab,
                                        mode='indeterminate',
                                        style='Custom.Horizontal.TProgressbar')

        # Configuration des tags pour le texte coloré
        for tag, color in [
            ('success', '#28a745'),
            ('error', '#dc3545'),
            ('warning', '#ffc107'),
            ('info', '#17a2b8'),
            ('device', '#007bff'),
            ('command', '#6f42c1'),
            ('found', '#10b981'),
            ('not_found', '#ef4444')
        ]:
            self.result_text.tag_config(tag, foreground=color)

        # Thread pour traiter les résultats en temps réel
        threading.Thread(
            target=self.process_results,
            daemon=True
        ).start()

    def setup_stats_section(self, parent):
        """Configure la section statistiques"""
        stats_frame = ttk.Frame(parent, style='Card.TFrame')
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Métriques principales
        metrics_frame = ttk.Frame(stats_frame, style='Card.TFrame')
        metrics_frame.pack(fill=tk.X, pady=10)

        metrics = [
            ("Équipements vérifiés:", "0", "info"),
            ("Commandes trouvées:", "0", "success"),
            ("Commandes absentes:", "0", "error"),
            ("En cours:", "0", "info")
        ]

        for i, (label, value, style) in enumerate(metrics):
            frame = ttk.Frame(metrics_frame, style='Card.TFrame')
            frame.grid(row=i // 2, column=i % 2, sticky='ew', padx=5, pady=5)

            ttk.Label(frame, text=label, style='TLabel').pack(side=tk.LEFT)
            ttk.Label(frame, text=value, style=f'{style}.TLabel',
                      font=('Segoe UI', 10, 'bold')).pack(side=tk.RIGHT)
            setattr(self, f'stat_{label.split(":")[0].lower().replace(" ", "_")}', frame.children['!label2'])

        # Graphique de répartition
        self.chart_canvas = tk.Canvas(stats_frame,
                                      height=150,
                                      bg='white',
                                      highlightthickness=0)
        self.chart_canvas.pack(fill=tk.X, pady=10)
        self.draw_placeholder_chart()

        # Détails des commandes
        ttk.Label(stats_frame,
                  text="Statut des commandes:",
                  style='TLabel').pack(anchor=tk.W, pady=5)

        self.commands_status = tk.Listbox(stats_frame,
                                          height=4,
                                          font=('Consolas', 9),
                                          bg='white',
                                          relief=tk.FLAT)
        self.commands_status.pack(fill=tk.X)

    def draw_placeholder_chart(self):
        """Dessine un graphique placeholder"""
        w = self.chart_canvas.winfo_width() or 400
        h = self.chart_canvas.winfo_height() or 150

        self.chart_canvas.delete('all')

        # Diagramme circulaire simulé
        center_x, center_y = w // 2, h // 2
        radius = min(w, h) // 3

        # Données simulées (70% trouvées, 30% absentes)
        self.chart_canvas.create_arc(center_x - radius, center_y - radius,
                                     center_x + radius, center_y + radius,
                                     start=0, extent=252, fill='#10b981', outline='')  # 70%
        self.chart_canvas.create_arc(center_x - radius, center_y - radius,
                                     center_x + radius, center_y + radius,
                                     start=252, extent=108, fill='#ef4444', outline='')  # 30%

        # Légende
        self.chart_canvas.create_text(center_x, center_y,
                                      text="70% trouvées",
                                      fill='white',
                                      font=('Segoe UI', 9, 'bold'))

        # Légendes extérieures
        self.chart_canvas.create_rectangle(20, 20, 40, 40, fill='#10b981', outline='')
        self.chart_canvas.create_text(60, 30, text="Commandes trouvées (70%)", anchor='w')

        self.chart_canvas.create_rectangle(20, 50, 40, 70, fill='#ef4444', outline='')
        self.chart_canvas.create_text(60, 70, text="Commandes absentes (30%)", anchor='w')

    def start_verification(self):
        """Démarre la vérification après validation"""
        # Vérification fichier Excel si nécessaire
        selected_tab = self.notebook.tab(self.notebook.select(), "text")

        if selected_tab == "Depuis Excel":
            if not hasattr(self.controller, 'chemin_equipement') or not self.controller.chemin_equipement:
                messagebox.showwarning(
                    "Fichier requis",
                    "Veuillez d'abord sélectionner un fichier Excel dans la page d'accueil"
                )
                self.controller.show_home()
                return
        elif selected_tab == "Plage IP":
            start_ip = self.start_ip.get().strip()
            end_ip = self.end_ip.get().strip()

            if not start_ip or not end_ip:
                messagebox.showwarning("Erreur", "Veuillez spécifier une plage IP valide")
                return

            # Validation simple des adresses IP
            try:
                from ipaddress import ip_address
                ip_address(start_ip)
                ip_address(end_ip)
            except ValueError:
                messagebox.showwarning("Erreur", "Adresse IP invalide")
                return

        elif selected_tab == "IPs spécifiques":
            ips = self.specific_ips_entry.get().strip()
            if not ips:
                messagebox.showwarning("Erreur", "Veuillez entrer au moins une adresse IP")
                return

            # Validation des IPs
            ip_list = [ip.strip() for ip in ips.split(',') if ip.strip()]
            if not ip_list:
                messagebox.showwarning("Erreur", "Aucune adresse IP valide trouvée")
                return

            try:
                from ipaddress import ip_address
                for ip in ip_list:
                    ip_address(ip)
            except ValueError:
                messagebox.showwarning("Erreur", f"Adresse IP invalide: {ip}")
                return

        # Vérification des commandes
        commands = self.commands_text.get(1.0, tk.END).strip().splitlines()
        if not commands:
            messagebox.showwarning("Erreur", "Aucune commande à vérifier")
            return

        # Demande des identifiants
        username = simpledialog.askstring("Authentification", "Nom d'utilisateur SSH:")
        if not username: return

        password = simpledialog.askstring("Authentification", "Mot de passe SSH:", show='*')
        if not password: return

        # Détermination des IPs cibles
        ip_list = None
        if selected_tab == "Plage IP":
            start_ip = self.start_ip.get().strip()
            end_ip = self.end_ip.get().strip()
            if not start_ip or not end_ip:
                messagebox.showwarning("Erreur", "Veuillez spécifier une plage IP valide")
                return
            ip_list = f"{start_ip}-{end_ip}"
        elif selected_tab == "IPs spécifiques":
            ips = self.specific_ips_entry.get().strip()
            if not ips:
                messagebox.showwarning("Erreur", "Veuillez entrer des adresses IP")
                return
            ip_list = ips

        # Préparation de l'interface
        self.clear_results()
        self.progress.pack(fill=tk.X, pady=5)
        self.progress.start()
        self.stop_verification_flag = False
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        # Réinitialisation des statistiques
        self.stat_équipements_vérifiés.config(text="0")
        self.stat_commandes_trouvées.config(text="0")
        self.stat_commandes_absentes.config(text="0")
        self.stat_en_cours.config(text="1")

        # Lancement de la vérification
        threading.Thread(
            target=self.execute_verification,
            args=(commands, username, password, ip_list),
            daemon=True
        ).start()

    def execute_verification(self, commands, username, password, ip_list=None):
        """Exécute la vérification dans un thread séparé"""
        try:
            # Lecture des équipements selon la méthode sélectionnée
            if ip_list and '-' in ip_list:  # Plage IP
                start_ip, end_ip = ip_list.split('-')
                devices = self.get_devices_from_ip_range(start_ip, end_ip)
            elif ip_list:  # IPs spécifiques
                devices = self.get_devices_from_specific_ips(ip_list.split(','))
            else:  # Depuis Excel
                devices = self.get_devices_from_excel()

            if not devices:
                self.result_queue.put(("⚠️ Aucun équipement à vérifier", 'warning'))
                return

            total_devices = len(devices)
            found_commands = set()
            missing_commands = set()

            # Vérification sur chaque équipement
            for idx, device in enumerate(devices, 1):
                if self.stop_verification_flag:
                    break

                self.result_queue.put((f"\n[🔍 {device['hostname']} ({device['ip']})", 'device'))
                self.result_queue.put(("🔌 Tentative de connexion...", None))
                self.stat_en_cours.config(text=f"{idx}/{total_devices}")

                try:
                    connection = ConnectHandler(
                        device_type=device['type'],
                        host=device['ip'],
                        username=username,
                        password=password,
                        secret=password,
                        timeout=10
                    )

                    self.result_queue.put((f"✅ Connecté ({connection.find_prompt()})", 'success'))
                    connection.enable()
                    config = connection.send_command("show running-config")
                    config_lines = config.splitlines()

                    # Vérification de chaque commande
                    device_found = []
                    for cmd in commands:
                        cmd = cmd.strip()
                        if not cmd:
                            continue

                        self.result_queue.put((f"🔎 Recherche: {cmd}", 'command'))

                        # Recherche exacte ligne par ligne
                        found_in_config = False
                        for line in config_lines:
                            if cmd.lower() == line.strip().lower():
                                found_in_config = True
                                break

                        if found_in_config:
                            self.result_queue.put((f"   ✅ Trouvé: {cmd}", 'found'))
                            device_found.append(cmd)
                            found_commands.add(cmd)
                        else:
                            # Vérification plus poussée pour les commandes partielles
                            if any(cmd.lower() in line.lower() for line in config_lines):
                                self.result_queue.put((f"   ⚠️ Partiellement trouvé: {cmd}", 'warning'))
                            else:
                                self.result_queue.put((f"   ❌ Non trouvé: {cmd}", 'not_found'))
                                missing_commands.add(cmd)

                    # Résumé pour cet équipement
                    self.result_queue.put(("\n📊 Résumé pour cet équipement:", 'command'))
                    if device_found:
                        self.result_queue.put((f"Commandes trouvées ({len(device_found)}):", None))
                        for cmd in device_found:
                            self.result_queue.put((f"  - {cmd}", 'found'))
                    else:
                        self.result_queue.put(("Aucune commande trouvée", 'warning'))

                    connection.disconnect()
                    self.stat_équipements_vérifiés.config(text=str(idx))

                except Exception as e:
                    error_msg = str(e)
                    if "TCP connection to device failed" in error_msg:
                        self.result_queue.put((f"❌ Erreur: {error_msg}\n\nCauses possibles:\n"
                                               "1. Adresse IP/hôte incorrect\n"
                                               "2. Port TCP incorrect\n"
                                               "3. Pare-feu intermédiaire\n", 'error'))
                    elif "Unsupported 'device_type'" in error_msg:
                        self.result_queue.put((f"❌ Erreur: Type d'équipement non supporté", 'error'))
                    else:
                        self.result_queue.put((f"❌ Erreur: {error_msg}", 'error'))

            # Mise à jour finale des statistiques
            if not self.stop_verification_flag:
                self.stat_commandes_trouvées.config(text=str(len(found_commands)))
                self.stat_commandes_absentes.config(text=str(len(missing_commands)))

                # Mise à jour du graphique
                total_cmds = len(commands)
                if total_cmds > 0:
                    found_percent = round(len(found_commands) / total_cmds * 100)
                    self.update_chart(found_percent, 100 - found_percent)

                # Mise à jour de la liste des commandes
                self.commands_status.delete(0, tk.END)
                for cmd in commands:
                    status = "✅" if cmd in found_commands else "❌"
                    self.commands_status.insert(tk.END, f"{status} {cmd}")

        except Exception as e:
            self.result_queue.put((f"❌ Erreur globale: {str(e)}", 'error'))
        finally:
            self.result_queue.put(("FINISHED", None))
            self.progress.stop()
            self.progress.pack_forget()
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.stat_en_cours.config(text="0")
            self.controller.update_status("Vérification terminée")

    def update_chart(self, found_percent, missing_percent):
        """Met à jour le graphique circulaire"""
        w = self.chart_canvas.winfo_width() or 400
        h = self.chart_canvas.winfo_height() or 150

        self.chart_canvas.delete('all')

        center_x, center_y = w // 2, h // 2
        radius = min(w, h) // 3

        # Nouveau diagramme avec les vraies valeurs
        self.chart_canvas.create_arc(center_x - radius, center_y - radius,
                                     center_x + radius, center_y + radius,
                                     start=0, extent=found_percent * 3.6,
                                     fill='#10b981', outline='')
        self.chart_canvas.create_arc(center_x - radius, center_y - radius,
                                     center_x + radius, center_y + radius,
                                     start=found_percent * 3.6, extent=missing_percent * 3.6,
                                     fill='#ef4444', outline='')

        # Texte au centre
        self.chart_canvas.create_text(center_x, center_y,
                                      text=f"{found_percent}% trouvées",
                                      fill='white',
                                      font=('Segoe UI', 9, 'bold'))

    def get_devices_from_excel(self):
        """Récupère les équipements depuis le fichier Excel"""
        try:
            df = pd.read_excel(self.controller.chemin_equipement, header=2)
            devices = []

            for _, row in df.iterrows():
                if row['Device Type'] == 'cisco_ios':
                    devices.append({
                        'hostname': row['Hostname'],
                        'ip': row['IP Address'],
                        'type': row['Device Type']
                    })

            return devices
        except Exception as e:
            self.result_queue.put((f"❌ Erreur lecture Excel: {str(e)}", 'error'))
            return []

    def get_devices_from_ip_range(self, start_ip, end_ip):
        """Génère une liste d'équipements à partir d'une plage IP"""
        # Cette implémentation est simplifiée - à adapter selon vos besoins
        try:
            from ipaddress import ip_address, summarize_address_range

            start = ip_address(start_ip)
            end = ip_address(end_ip)

            devices = []
            for ip in summarize_address_range(start, end):
                devices.append({
                    'hostname': f"ip-{ip}",
                    'ip': str(ip),
                    'type': 'cisco_ios'  # Supposition
                })

            return devices
        except Exception as e:
            self.result_queue.put((f"❌ Erreur plage IP: {str(e)}", 'error'))
            return []

    def get_devices_from_specific_ips(self, ips):
        """Crée une liste d'équipements à partir d'IPs spécifiques"""
        return [{
            'hostname': f"ip-{ip.strip()}",
            'ip': ip.strip(),
            'type': 'cisco_ios'  # Supposition
        } for ip in ips if ip.strip()]

    def process_results(self):
        """Traite les résultats au fur et à mesure qu'ils arrivent"""
        while True:
            result = self.result_queue.get()
            if result == "FINISHED":
                break

            message, tag = result
            self.log_result(message, tag)

    def stop_verification(self):
        """Arrête la vérification en cours"""
        self.stop_verification_flag = True
        self.log_result("🛑 Vérification arrêtée par l'utilisateur", 'warning')
        self.controller.update_status("Vérification arrêtée")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.stat_en_cours.config(text="0")

    def clear_results(self):
        """Efface les résultats"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.config(state=tk.DISABLED)

        # Réinitialisation des statistiques
        self.stat_équipements_vérifiés.config(text="0")
        self.stat_commandes_trouvées.config(text="0")
        self.stat_commandes_absentes.config(text="0")

        # Réinitialisation du graphique
        self.draw_placeholder_chart()

        # Vidage de la liste des commandes
        self.commands_status.delete(0, tk.END)

    def log_result(self, message, tag=None):
        """Ajoute un message aux résultats"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.insert(tk.END, message + "\n", tag)
        self.result_text.see(tk.END)
        self.result_text.config(state=tk.DISABLED)

    def export_results(self):
        """Exporte les résultats vers un fichier"""
        if not self.result_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Aucun résultat", "Aucun résultat à exporter")
            return

        file_path = filedialog.asksaveasfilename(
            title="Exporter les résultats",
            defaultextension=".txt",
            filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")]
        )

        if file_path:
            try:
                self.result_text.config(state=tk.NORMAL)
                content = self.result_text.get(1.0, tk.END)
                self.result_text.config(state=tk.DISABLED)

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.log_result(f"✅ Résultats exportés vers {file_path}", 'success')
                messagebox.showinfo("Succès", "Exportation terminée")
            except Exception as e:
                self.log_result(f"❌ Erreur export: {str(e)}", 'error')
                messagebox.showerror("Erreur", f"Échec de l'export: {str(e)}")

    def update_path_display(self):
        """Met à jour l'affichage du chemin Excel"""
        if hasattr(self.controller, 'chemin_equipement') and self.controller.chemin_equipement:
            self.excel_status.config(
                text=f"Fichier sélectionné: {os.path.basename(self.controller.chemin_equipement)}",
                style='TLabel'
            )
        else:
            self.excel_status.config(
                text="Aucun fichier sélectionné (aller à la page Accueil)",
                style='Warning.TLabel'
            )

    def on_show(self):
        """Exécuté lorsque la page est affichée"""
        self.controller.update_status("Page de vérification - Prêt")
        self.update_path_display()


class ModernChatFrame(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, style='Content.TFrame')
        self.controller = controller
        self.chat_history = []
        self.is_processing = False
        self.current_model = tk.StringVar(value="gemma:2b")  # Modèle par défaut

        # Configuration de l'interface
        self.setup_ui()

    def setup_ui(self):
        """Configure l'interface utilisateur moderne"""
        container = ttk.Frame(self, style='Content.TFrame')
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Header avec style cohérent
        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header,
                  text="🤖 Assistant Réseau",
                  style='Title.TLabel',
                  font=('Segoe UI', 18, 'bold')).pack(side=tk.LEFT)

        # Section configuration
        config_frame = ttk.LabelFrame(container,
                                      text=" Configuration ",
                                      style='Card.TFrame',
                                      padding=10)
        config_frame.pack(fill=tk.X, pady=(0, 10))

        # Sélection du modèle
        model_frame = ttk.Frame(config_frame, style='Card.TFrame')
        model_frame.pack(fill=tk.X, pady=5)

        ttk.Label(model_frame, text="Modèle IA:", style='TLabel').pack(side=tk.LEFT, padx=5)

        self.model_selector = ttk.Combobox(
            model_frame,
            textvariable=self.current_model,
            values=["gemma:2b", "llama2", "mistral"],
            state="readonly",
            width=15
        )
        self.model_selector.pack(side=tk.LEFT, padx=5)

        ttk.Button(model_frame,
                   text="🔄 Vérifier",
                   command=self.check_available_models,
                   style='Toolbutton').pack(side=tk.RIGHT, padx=5)

        # Conteneur principal pour la zone de chat avec scrollbar
        chat_container = ttk.Frame(container, style='Card.TFrame')
        chat_container.pack(fill=tk.BOTH, expand=True, pady=10)

        # Cadre de défilement
        self.chat_frame = ttk.Frame(chat_container, style='Card.TFrame')

        # Canvas et Scrollbar
        self.canvas = tk.Canvas(chat_container, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(chat_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style='Card.TFrame')

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Empilement des widgets
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Zone de saisie
        input_frame = ttk.Frame(container, style='Input.TFrame')
        input_frame.pack(fill=tk.X, pady=(10, 0))

        self.user_input = ttk.Entry(
            input_frame,
            font=('Segoe UI', 11),
            style='Modern.TEntry'
        )
        self.user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.user_input.bind("<Return>", lambda e: self.send_message())

        send_btn = ttk.Button(
            input_frame,
            text="Envoyer",
            command=self.send_message,
            style='Accent.TButton'
        )
        send_btn.pack(side=tk.RIGHT, padx=5)

        # Boutons supplémentaires
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame,
                   text="Effacer la conversation",
                   command=self.clear_chat,
                   style='Danger.TButton').pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame,
                   text="Exporter la conversation",
                   command=self.export_chat,
                   style='Info.TButton').pack(side=tk.RIGHT, padx=5)

        # Barre de statut
        self.status_var = tk.StringVar(value="Prêt à discuter")
        status_bar = ttk.Frame(container, style='Status.TFrame')
        status_bar.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(status_bar,
                  textvariable=self.status_var,
                  style='Status.TLabel').pack(side=tk.LEFT, padx=10)

        # Message de bienvenue
        self.add_message("assistant",
                         "Bonjour ! Je suis votre assistant réseau. Posez-moi vos questions sur Cisco, les configurations réseau ou le dépannage.")

    def add_message(self, sender, message):
        """Ajoute un message à la conversation"""
        frame = ttk.Frame(self.scrollable_frame, style='Card.TFrame')
        frame.pack(fill=tk.X, pady=5, padx=5, anchor='w' if sender == 'assistant' else 'e')

        # Style différent selon l'expéditeur
        style = 'Assistant.TLabel' if sender == 'assistant' else 'User.TLabel'

        msg_label = ttk.Label(
            frame,
            text=message,
            style=style,
            wraplength=400
        )
        msg_label.pack(fill=tk.X, padx=5, pady=2)

        # Ajout à l'historique
        self.chat_history.append((sender, message))

        # Mise à jour du défilement
        self.canvas.yview_moveto(1.0)
        self.update_idletasks()

    def send_message(self):
        """Envoie le message de l'utilisateur"""
        message = self.user_input.get().strip()
        if not message or self.is_processing:
            return

        self.user_input.delete(0, tk.END)
        self.add_message("user", message)
        self.status_var.set("Traitement en cours...")
        self.is_processing = True

        # Désactiver le champ de saisie pendant le traitement
        self.user_input.config(state=tk.DISABLED)

        # Envoi dans un thread séparé
        threading.Thread(
            target=self.process_user_message,
            args=(message,),
            daemon=True
        ).start()

    def process_user_message(self, message):
        """Traite le message de l'utilisateur avec Ollama"""
        try:
            # Simuler un temps de traitement
            time.sleep(1)

            # Ici vous devriez implémenter l'appel réel à l'API Ollama
            # Pour l'exemple, nous allons simuler une réponse
            response_text = f"Réponse simulée pour: {message}"

            # En production, utilisez plutôt:
            # import ollama
            # response = ollama.generate(model=self.current_model.get(), prompt=message)
            # response_text = response['response']

            self.add_message("assistant", response_text)

        except Exception as e:
            error_msg = f"Erreur avec le modèle {self.current_model.get()}: {str(e)}"
            self.add_message("system", error_msg)

        finally:
            self.status_var.set("Prêt à discuter")
            self.is_processing = False
            self.user_input.config(state=tk.NORMAL)
            self.user_input.focus()

    def check_available_models(self):
        """Vérifie les modèles disponibles via Ollama"""
        try:
            # Simuler la vérification des modèles
            # En production, utilisez:
            # import ollama
            # models = [model['name'] for model in ollama.list()['models']]

            models = ["gemma:2b", "llama2", "mistral"]  # Simulation
            self.model_selector['values'] = models
            self.add_message("system", f"Modèles disponibles: {', '.join(models)}")
        except Exception as e:
            self.add_message("system", f"Impossible de vérifier les modèles: {str(e)}")

    def clear_chat(self):
        """Efface la conversation"""
        if self.is_processing:
            return

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.chat_history = []
        self.add_message("assistant", "Conversation réinitialisée. Posez-moi vos questions réseau !")

    def export_chat(self):
        """Exporte la conversation vers un fichier"""
        if not self.chat_history or self.is_processing:
            return

        file_path = filedialog.asksaveasfilename(
            title="Exporter la conversation",
            defaultextension=".txt",
            filetypes=[("Fichiers texte", "*.txt"), ("Tous les fichiers", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for sender, msg in self.chat_history:
                        f.write(f"{sender.upper()}: {msg}\n\n")
                self.add_message("system", f"Conversation exportée vers {file_path}")
            except Exception as e:
                self.add_message("system", f"Erreur lors de l'export: {str(e)}")

    def on_show(self):
        """Exécuté lorsque la page est affichée"""
        self.controller.update_status("Assistant réseau - Prêt")
        # Vérification initiale des modèles
        threading.Thread(target=self.check_available_models, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernNetworkAutomationApp(root)
    root.mainloop()


