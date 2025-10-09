import json
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import re


class ChatEngine:
    def __init__(self, knowledge_path: str = 'knowledge_base.json'):
        """Initialise avec chargement du modèle et de la base de connaissances"""
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.knowledge_base = self.load_knowledge_base(knowledge_path)
        self.precompute_embeddings()

    def load_knowledge_base(self, path: str) -> Dict:
        """Charge la base de connaissances avec vérification"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data.get("questions"), list):
                    raise ValueError("Format invalide: la base doit contenir une liste 'questions'")
                return data
        except Exception as e:
            raise RuntimeError(f"Erreur chargement knowledge base: {str(e)}")

    def precompute_embeddings(self):
        """Pré-calcule les embeddings pour toutes les questions"""
        self.questions = [q["question"] for q in self.knowledge_base["questions"]]
        self.question_embeddings = self.model.encode(self.questions)

    def extract_network_context(self, question: str) -> str:
        """Détecte le contexte réseau (routeur, switch, VLAN, etc.)"""
        question_lower = question.lower()
        contexts = {
            'routeur': ['routeur', 'router', 'bgp', 'ospf', 'eigrp'],
            'switch': ['switch', 'commutateur', 'vlan', 'trunk', 'stp'],
            'vpn': ['vpn', 'ipsec', 'gre'],
            'sécurité': ['acl', 'firewall', 'sécurité', 'security']
        }

        for context, keywords in contexts.items():
            if any(kw in question_lower for kw in keywords):
                return context
        return 'général'

    def enhanced_semantic_search(self, user_question: str, context: str = None) -> Optional[int]:
        """Recherche sémantique avec prise en compte du contexte"""
        user_embedding = self.model.encode([user_question])[0]
        similarities = np.dot(self.question_embeddings, user_embedding)

        # Combinaison avec le contexte
        scores = []
        for idx, item in enumerate(self.knowledge_base["questions"]):
            score = similarities[idx]

            # Bonus pour correspondance de contexte
            if context and context in item.get("contexts", ['général']):
                score *= 1.2

            scores.append((score, idx))

        if not scores:
            return None

        best_match_idx = max(scores, key=lambda x: x[0])[1]
        return best_match_idx if scores[best_match_idx][0] >= 0.7 else None  # Seuil ajustable

    def keyword_search(self, user_question: str, context: str = None) -> Optional[str]:
        """Recherche par mots-clés avec pondération"""
        user_words = set(re.findall(r'\w+', user_question.lower()))
        best_score = 0
        best_answer = None

        for item in self.knowledge_base["questions"]:
            # Score de base
            score = sum(1 for kw in item["keywords"] if kw.lower() in user_words)

            # Bonus pour variantes exactes
            if any(v.lower() in user_question.lower() for v in item.get("variantes", [])):
                score += 2

            # Bonus pour contexte
            if context and context in item.get("contexts", ['général']):
                score *= 1.5

            if score > best_score:
                best_score = score
                best_answer = item["answer"]

        return best_answer if best_score >= 2 else None  # Au moins 2 mots-clés

    def format_response(self, answer: str) -> str:
        """Formate la réponse avec mise en forme des commandes Cisco"""
        # Détection des blocs de code
        answer = re.sub(r'`(.+?)`', r'```\n\1\n```', answer)

        # Ajout de sauts de ligne après les titres
        answer = re.sub(r'(## .+)', r'\1\n', answer)

        return answer

    def get_response(self, user_question: str) -> Optional[str]:
        """Orchestre la recherche de réponse avec priorisation"""
        if not user_question.strip():
            return None

        context = self.extract_network_context(user_question)

        # 1. Recherche sémantique améliorée
        if match_idx := self.enhanced_semantic_search(user_question, context):
            answer = self.knowledge_base["questions"][match_idx]["answer"]
            return self.format_response(answer)

        # 2. Recherche par mots-clés contextuelle
        if answer := self.keyword_search(user_question, context):
            return self.format_response(answer)

        return None

    def add_temporary_entry(self, question: str, answer: str, keywords: List[str] = None):
        """Ajoute temporairement une entrée (non persistante)"""
        new_entry = {
            "question": question,
            "answer": answer,
            "keywords": keywords or [],
            "variantes": [],
            "contexts": [self.extract_network_context(question)]
        }
        self.knowledge_base["questions"].append(new_entry)
        self.precompute_embeddings()  # Mise à jour des embeddings



