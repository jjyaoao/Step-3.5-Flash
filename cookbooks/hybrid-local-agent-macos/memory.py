import json
import os
import uuid
import math

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MEMORY_FILE = os.path.join(DATA_DIR, "jarvis_memory.json")

# On s'assure que le dossier data existe
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# --- GESTION DU FICHIER JSON ---
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def save_memory(memories):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memories, f, indent=2, ensure_ascii=False)

# --- FONCTIONS CLÉS ---

def add_memory(content: str, category: str = "general") -> str:
    """
    Sauvegarde une info dans le fichier JSON.
    """
    memories = load_memory()
    
    new_memory = {
        "id": str(uuid.uuid4()),
        "content": content,
        "category": category,
        "timestamp": "now" # Tu pourrais mettre un time.time()
    }
    
    memories.append(new_memory)
    save_memory(memories)
    
    return f"✅ Info sauvegardée dans la mémoire légère : '{content}'"

def search_memory(query: str, n_results: int = 3) -> str:
    """
    Recherche par MOTS-CLÉS (Simple et Robuste).
    """
    memories = load_memory()
    if not memories:
        return "Mémoire vide."

    # Système de scoring simple : on compte les mots communs
    query_words = set(query.lower().split())
    ranked_memories = []

    for mem in memories:
        mem_words = set(mem["content"].lower().split())
        # Nombre de mots en commun
        score = len(query_words.intersection(mem_words))
        if score > 0:
            ranked_memories.append((score, mem["content"]))

    # On trie par score décroissant
    ranked_memories.sort(key=lambda x: x[0], reverse=True)

    # On garde les meilleurs
    top_results = ranked_memories[:n_results]

    if not top_results:
        return "Aucune info pertinente trouvée."

    output = "🔍 INFOS MÉMOIRE (JSON) :\n"
    for score, text in top_results:
        output += f"- {text}\n"

    return output

if __name__ == "__main__":
    # Petit test
    print(add_memory("Le code secret est Banane42."))
    print(search_memory("C'est quoi le code secret ?"))