import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import ollama
import queue
import json
import pyperclip
import re
from tkinter.font import Font
import numpy as np
from sentence_transformers import SentenceTransformer
import sys
#ollama.Client(host='http://localhost:11435')  # Utilisez le nouveau port

class ModernChatFrame(ttk.Frame):
    def __init__(self, parent, controller):
        ttk.Frame.__init__(self, parent, style='Content.TFrame')
        self.controller = controller
        self.setup_ui()
        self.setup_engine()
        self.message_queue = queue.Queue()
        self.current_typing_effect = None
        self.check_queue()

    def setup_engine(self):
        """Initialise le moteur de recherche sémantique"""
        try:
            self.semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
            with open('knowledge_base.json', 'r', encoding='utf-8') as f:
                self.knowledge_base = json.load(f)
        except Exception as e:
            self.log_error(f"Erreur initialisation: {str(e)}")

    def setup_ui(self):
        """Interface style DeepSeek avec boutons de copie/modification"""
        container = ttk.Frame(self, style='Content.TFrame')
        container.pack(fill=tk.BOTH, expand=True)

        # PanedWindow pour redimensionnement
        paned = ttk.PanedWindow(container, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Zone de conversation (70%)
        conv_frame = ttk.Frame(paned)
        self.chat_display = scrolledtext.ScrolledText(
            conv_frame,
            wrap=tk.WORD,
            font=('Segoe UI', 11),
            padx=20,
            pady=15,
            state='disabled',
            background='#f8fafc',
            spacing1=5,
            spacing2=2,
            spacing3=5
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        self.configure_tags()
        paned.add(conv_frame, weight=7)

        # Zone de saisie (30%)
        input_frame = ttk.Frame(paned)
        input_container = ttk.Frame(input_frame, padding=10)
        input_container.pack(fill=tk.BOTH, expand=True)

        self.user_input = tk.Text(
            input_container,
            height=5,
            wrap=tk.WORD,
            font=('Segoe UI', 12),
            padx=15,
            pady=12,
            bg='white',
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#e5e7eb",
            highlightcolor="#3b82f6",
            insertbackground='black'
        )
        self.user_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Button(
            input_container,
            text="➤",
            command=self.send_message,
            style='Arrow.TButton',
            width=3
        ).pack(side=tk.RIGHT, padx=(10, 0))

        self.user_input.bind("<Return>", lambda e: self.send_message())
        paned.add(input_frame, weight=3)

        # Message de bienvenue
        self.add_message("system",
                         "Bonjour ! Je suis votre assistant réseau Cisco. Posez-moi vos questions techniques.")

    def configure_tags(self):
        """Styles unifiés pour les messages"""
        # Style UTILISATEUR (droite - simple)
        self.chat_display.tag_config('user',
                                     foreground='#1a56db',
                                     font=('Segoe UI', 11),
                                     lmargin1=100,
                                     lmargin2=120,
                                     rmargin=20,
                                     spacing3=8
                                     )

        # Style ASSISTANT (gauche - fond vert)
        self.chat_display.tag_config('assistant',
                                     foreground='#065f46',
                                     font=('Segoe UI', 11),
                                     lmargin1=20,
                                     lmargin2=40,
                                     rmargin=100,
                                     spacing3=8,
                                     background='#ecfdf5'
                                     )

        # Style SYSTÈME
        self.chat_display.tag_config('system',
                                     foreground='#6b7280',
                                     font=('Segoe UI', 9, 'italic')
                                     )

        # Style pour les boutons d'action
        self.chat_display.tag_config('button_area',
                                     spacing3=10
                                     )

    def add_message(self, sender, message, typing_effect=True):
        """Ajoute un message avec options de copie/modification"""
        self.chat_display.config(state='normal')

        if sender == "user":
            prefix = "👤 Vous:"
            tag = 'user'
            self.chat_display.insert('end', f"{prefix}\n{message}\n", tag)
            self.add_action_buttons(message, is_user=True)

        elif sender == "assistant":
            prefix = "🤖 Assistant:"
            tag = 'assistant'
            self.chat_display.insert('end', f"{prefix}\n", tag)

            if typing_effect:
                if self.current_typing_effect:
                    self.after_cancel(self.current_typing_effect)
                self.type_message(message, tag)
            else:
                self.chat_display.insert('end', f"{message}\n", tag)
                self.add_action_buttons(message, is_user=False)

        else:  # system
            prefix = "⚙️ Système:"
            tag = 'system'
            self.chat_display.insert('end', f"{prefix}\n{message}\n\n", tag)

        self.chat_display.config(state='disabled')
        self.chat_display.see('end')

    def add_action_buttons(self, message, is_user):
        """Ajoute des boutons d'action fixes pour les messages"""
        button_frame = ttk.Frame(self.chat_display)

        # Bouton Copier (toujours présent)
        copy_btn = ttk.Button(
            button_frame,
            text="📋",
            command=lambda: self.copy_message(message),
            style='Tool.TButton',
            width=2
        )
        copy_btn.pack(side=tk.LEFT, padx=2)
        self.setup_tooltip(copy_btn, "Copier")

        # Bouton Modifier (uniquement pour les messages utilisateur)
        if is_user:
            edit_btn = ttk.Button(
                button_frame,
                text="✏️",
                command=lambda: self.edit_message(message),
                style='Tool.TButton',
                width=2
            )
            edit_btn.pack(side=tk.LEFT, padx=2)
            self.setup_tooltip(edit_btn, "Modifier")

        # Insertion des boutons dans le chat
        self.chat_display.window_create('end', window=button_frame)
        self.chat_display.insert('end', '\n', 'button_area')

    def setup_tooltip(self, widget, text):
        """Configure un tooltip au survol"""

        def enter(event):
            self.show_tooltip(widget, text)

        def leave(event):
            self.hide_tooltip()

        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def show_tooltip(self, widget, text):
        """Affiche un tooltip au survol"""
        if hasattr(self, 'tooltip'):
            self.hide_tooltip()

        x = widget.winfo_rootx() + 10
        y = widget.winfo_rooty() + 25

        self.tooltip = tk.Toplevel(widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(
            self.tooltip,
            text=text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padding=(2, 1)
        )
        label.pack()

    def hide_tooltip(self):
        """Cache le tooltip"""
        if hasattr(self, 'tooltip'):
            self.tooltip.destroy()
            del self.tooltip

    def copy_message(self, message):
        """Copie le message dans le presse-papiers"""
        pyperclip.copy(message)
        self.show_temporary_tooltip("Copié !")

    def edit_message(self, message):
        """Réaffiche le message pour modification"""
        self.user_input.delete('1.0', tk.END)
        self.user_input.insert('1.0', message)
        self.user_input.focus_set()
        self.show_temporary_tooltip("Prêt à modifier")

    def show_temporary_tooltip(self, text):
        """Affiche un message temporaire après action"""
        x = self.winfo_pointerx() + 10
        y = self.winfo_pointery() + 10

        tooltip = tk.Toplevel(self)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(
            tooltip,
            text=text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padding=(2, 1)
        )
        label.pack()

        self.after(1000, tooltip.destroy)

    def type_message(self, message, tag, index=0):
        """Effet de frappe avec gestion des boutons"""
        if index < len(message):
            char = message[index]
            self.chat_display.config(state='normal')
            self.chat_display.insert('end', char, tag)
            self.chat_display.config(state='disabled')
            self.chat_display.see('end')

            delay = 10 if char in '.,;!? ' else 30
            self.current_typing_effect = self.after(delay, lambda: self.type_message(message, tag, index + 1))
        else:
            self.chat_display.config(state='normal')
            self.chat_display.insert('end', '\n', tag)
            self.add_action_buttons(message, is_user=False)
            self.chat_display.config(state='disabled')
            self.current_typing_effect = None

    def send_message(self, event=None):
        """Gère l'envoi avec priorité au JSON et contexte approprié"""
        user_msg = self.user_input.get("1.0", tk.END).strip()
        if not user_msg:
            return

        self.add_message("user", user_msg)
        self.user_input.delete("1.0", tk.END)

        # Détection du type d'équipement demandé
        device_type = self.detect_device_type(user_msg)

        # 1. Recherche dans la base locale avec contexte
        if answer := self.find_in_knowledge(user_msg, device_type):
            self.add_message("assistant", answer)
        else:
            # 2. Fallback sur Ollama avec contexte
            threading.Thread(
                target=self.get_contextual_response,
                args=(user_msg, device_type),
                daemon=True
            ).start()

    def detect_device_type(self, question):
        """Détecte le type d'équipement dans la question"""
        question_lower = question.lower()

        if 'routeur' in question_lower or 'router' in question_lower:
            return 'routeur'
        elif 'switch' in question_lower or 'commutateur' in question_lower:
            return 'switch'
        elif 'vlan' in question_lower:
            return 'vlan'
        else:
            return 'general'

    def find_in_knowledge(self, question, device_type):
        """Recherche intelligente dans le JSON avec contexte"""
        try:
            # 1. Matching exact avec type d'équipement
            for item in self.knowledge_base["questions"]:
                if (question.lower() == item["question"].lower() and
                        device_type in item.get("device_types", ["general"])):
                    return item["answer"]

            # 2. Matching par variantes avec type d'équipement
            for item in self.knowledge_base["questions"]:
                variants = item.get("variantes", [])
                if (any(v.lower() in question.lower() for v in variants) and
                        device_type in item.get("device_types", ["general"])):
                    return item["answer"]

            # 3. Matching par mots-clés
            user_words = set(question.lower().split())
            for item in self.knowledge_base["questions"]:
                if any(kw.lower() in user_words for kw in item["keywords"]):
                    return item["answer"]

            # 4. Matching sémantique
            questions = [q["question"] for q in self.knowledge_base["questions"]]
            embeddings = self.semantic_model.encode(questions + [question])
            similarities = np.dot(embeddings[:-1], embeddings[-1])

            if np.max(similarities) > 0.7:  # Seuil de similarité
                best_match = self.knowledge_base["questions"][np.argmax(similarities)]
                if device_type in best_match.get("device_types", ["general"]):
                    return best_match["answer"]

        except Exception as e:
            self.log_error(f"Erreur recherche: {str(e)}")
        return None

    def get_contextual_response(self, prompt, device_type):
        """Génère une réponse contextuelle avec Ollama"""
        try:
            context_map = {
                'routeur': "Tu es un expert routeur Cisco. Donne des commandes précises pour les routeurs.",
                'switch': "Tu es un expert switch Cisco. Donne des commandes précises pour les commutateurs.",
                'vlan': "Tu es un expert VLAN Cisco. Donne des commandes précises pour la configuration VLAN.",
                'general': "Tu es un ingénieur réseau Cisco. Réponds de manière technique mais claire."
            }

            context = context_map.get(device_type, context_map['general'])

            response = ollama.generate(
                model='gemma:2b',
                prompt=f"""
                [CONTEXTE] {context}
                [QUESTION] {prompt}
                [REPONSE]""",
                options={'temperature': 0.3}
            )
            self.message_queue.put(("assistant", response['response'].strip()))
        except Exception as e:
            error_msg = f"Erreur Ollama: {str(e)}\nVérifiez que le service est lancé."
            self.message_queue.put(("system", error_msg))

    def check_queue(self):
        """Vérifie les messages en attente"""
        try:
            while True:
                sender, content = self.message_queue.get_nowait()
                self.add_message(sender, content)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.check_queue)

    def log_error(self, message):
        """Journalisation des erreurs"""
        print(f"[ERREUR] {message}")
        self.message_queue.put(("system", "⚠️ Erreur système - Voir les logs"))

    def on_show(self):
        """Focus sur la zone de saisie"""
        self.user_input.focus_set()
        self.controller.update_status("Assistant réseau - Prêt")

    def destroy(self):
        """Nettoyage"""
        if self.current_typing_effect:
            self.after_cancel(self.current_typing_effect)
        super().destroy()


