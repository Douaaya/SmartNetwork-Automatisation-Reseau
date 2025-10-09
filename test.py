from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
import os

model_name = "google/flan-t5-base"

# Récupération du token depuis une variable d'environnement (jamais en clair dans le code)
hf_token = os.getenv("HF_TOKEN")

tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)
model = AutoModelForSeq2SeqLM.from_pretrained(
    model_name,
    from_tf=True,
    torch_dtype=torch.float32,
    token=hf_token
)

print("Modèle chargé avec succès ✅")
