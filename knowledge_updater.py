import json
from datetime import datetime
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
import re
import os


class KnowledgeUpdater:
    def __init__(self, knowledge_path: str = 'knowledge_base.json'):
        """Initialise avec chargement du modèle NLP et de la base"""
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.knowledge_path = knowledge_path
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self) -> Dict:
        """Charge la base de connaissances avec création si inexistante"""
        try:
            if not os.path.exists(self.knowledge_path):
                base_structure = {"questions": [], "metadata": {"created": datetime.now().isoformat()}}
                with open(self.knowledge_path, 'w', encoding='utf-8') as f:
                    json.dump(base_structure, f, indent=2)
                return base_structure

            with open(self.knowledge_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "questions" not in data:
                    data["questions"] = []
                return data
        except Exception as e:
            raise RuntimeError(f"Erreur chargement knowledge base: {str(e)}")

    def _auto_generate_keywords(self, text: str) -> List[str]:
        """Génère automatiquement des mots-clés pertinents"""
        words = re.findall(r'\w{4,}', text.lower())  # Ignore les mots courts
        embeddings = self.model.encode(words)

        # Clusterisation simple pour trouver les mots centraux
        if len(embeddings) > 3:
            centroid = np.mean(embeddings, axis=0)
            similarities = np.dot(embeddings, centroid)
            top_indices = np.argsort(similarities)[-3:]  # Prend les 3 mots les plus centraux
            return [words[i] for i in top_indices]
        return words

    def _find_similar_questions(self, question: str, threshold: float = 0.85) -> Optional[int]:
        """Trouve des questions similaires existantes"""
        questions = [q["question"] for q in self.knowledge_base["questions"]]
        if not questions:
            return None

        embeddings = self.model.encode(questions + [question])
        similarities = np.dot(embeddings[:-1], embeddings[-1])
        best_match_idx = np.argmax(similarities)
        return best_match_idx if similarities[best_match_idx] >= threshold else None

    def add_entry(self, question: str, answer: str,
                  keywords: Optional[List[str]] = None,
                  variantes: Optional[List[str]] = None,
                  auto_keywords: bool = True,
                  check_duplicates: bool = True) -> bool:
        """
        Ajoute une entrée à la base de connaissances avec options avancées

        Args:
            question: La question à ajouter
            answer: La réponse associée
            keywords: Mots-clés manuels (optionnel)
            variantes: Variantes de formulation (optionnel)
            auto_keywords: Génère des mots-clés automatiquement si True
            check_duplicates: Vérifie les doublons si True

        Returns:
            bool: True si ajout réussi, False si doublon détecté
        """
        if check_duplicates:
            if duplicate_idx := self._find_similar_questions(question):
                existing = self.knowledge_base["questions"][duplicate_idx]
                print(f"Doublon potentiel détecté avec l'entrée existante: {existing['question']}")
                return False

        # Génération automatique des mots-clés si besoin
        final_keywords = keywords if keywords else []
        if auto_keywords and not keywords:
            final_keywords.extend(self._auto_generate_keywords(question + " " + answer))

        new_entry = {
            "question": question,
            "answer": answer,
            "keywords": list(set(final_keywords)),  # Élimine les doublons
            "variantes": variantes or [],
            "metadata": {
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "source": "manual"
            }
        }

        self.knowledge_base["questions"].append(new_entry)
        self._save_knowledge_base()
        return True

    def update_entry(self, question_id: int, **kwargs):
        """Met à jour une entrée existante"""
        valid_fields = {"question", "answer", "keywords", "variantes"}
        if question_id < 0 or question_id >= len(self.knowledge_base["questions"]):
            raise ValueError("ID d'entrée invalide")

        entry = self.knowledge_base["questions"][question_id]
        for field, value in kwargs.items():
            if field in valid_fields:
                entry[field] = value
        entry["metadata"]["last_updated"] = datetime.now().isoformat()
        self._save_knowledge_base()

    def remove_entry(self, question_id: int):
        """Supprime une entrée de la base"""
        if 0 <= question_id < len(self.knowledge_base["questions"]):
            self.knowledge_base["questions"].pop(question_id)
            self._save_knowledge_base()

    def _save_knowledge_base(self):
        """Sauvegarde la base de connaissances avec gestion des erreurs"""
        try:
            with open(self.knowledge_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"Erreur sauvegarde knowledge base: {str(e)}")

    def export_from_log(self, log_file: str = "chat_log.txt", min_occurrences: int = 3):
        """
        Extrait automatiquement des connaissances des logs de chat

        Args:
            log_file: Chemin vers le fichier de logs
            min_occurrences: Nombre minimum d'occurrences pour considérer une question comme importante
        """
        if not os.path.exists(log_file):
            print(f"Fichier de log {log_file} introuvable")
            return

        # Implémentation basique - à adapter selon votre format de logs
        try:
            from collections import defaultdict
            question_counts = defaultdict(int)
            qa_pairs = defaultdict(list)

            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if "Question:" in line:
                        question = line.split("Question:")[1].strip()
                        question_counts[question] += 1
                    elif "Answer:" in line and question:
                        answer = line.split("Answer:")[1].strip()
                        qa_pairs[question].append(answer)

            # Ajout des questions fréquentes
            added = 0
            for q, count in question_counts.items():
                if count >= min_occurrences and q in qa_pairs:
                    best_answer = max(qa_pairs[q], key=len)  # Prend la réponse la plus longue
                    if self.add_entry(q, best_answer, auto_keywords=True, check_duplicates=True):
                        added += 1

            print(f"Export terminé. {added} nouvelles entrées ajoutées.")

        except Exception as e:
            print(f"Erreur lors de l'export depuis les logs: {str(e)}")

    def backup_knowledge_base(self, backup_dir: str = "backups"):
        """Crée une sauvegarde datée de la base de connaissances"""
        try:
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(
                backup_dir,
                f"knowledge_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False)
            return backup_path
        except Exception as e:
            print(f"Erreur lors de la sauvegarde: {str(e)}")
            return None


