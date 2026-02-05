import json
import math
import os
import re
import time
import uuid
import hashlib

try:
    import chromadb
except Exception:
    chromadb = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

CHROMA_DIR = os.path.join(DATA_DIR, "chroma")
FALLBACK_FILE = os.path.join(DATA_DIR, "rag_fallback.jsonl")
COLLECTION_NAME = "conversation_rag"

EMBED_DIM = 256
MAX_TEXT_CHARS = 6000
DEFAULT_EMBED_BACKEND = os.environ.get("RAG_EMBED_BACKEND", "lmstudio").strip().lower()
DEFAULT_EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "auto").strip()
DEFAULT_QUERY_PROMPT = os.environ.get("RAG_EMBED_QUERY_PROMPT", "query").strip() or None
DEFAULT_QUERY_INSTRUCTION = os.environ.get("RAG_EMBED_QUERY_INSTRUCTION", "").strip()
DEFAULT_EMBED_DEVICE = os.environ.get("RAG_EMBED_DEVICE", "").strip()
DEFAULT_LMSTUDIO_URL = os.environ.get("RAG_EMBED_LMSTUDIO_URL", "http://localhost:1234/v1").strip()
DEFAULT_LMSTUDIO_DIM = os.environ.get("RAG_EMBED_LMSTUDIO_DIM", "").strip()


class SimpleEmbeddingFunction:
    def __init__(self, dim: int = EMBED_DIM):
        self.dim = dim

    def name(self) -> str:
        return f"simple-hash-{self.dim}"

    def __call__(self, input):
        texts = [input] if isinstance(input, str) else list(input or [])
        return [self._embed(text or "") for text in texts]

    def embed_documents(self, input):
        return self.__call__(input)

    def embed_query(self, input):
        return self.__call__(input)

    def _embed(self, text: str) -> list[float]:
        tokens = re.findall(r"[\\w\\-]+", text.lower())
        if not tokens:
            return [0.0] * self.dim
        vec = [0.0] * self.dim
        for token in tokens:
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

class SentenceTransformerEmbeddingFunction:
    def __init__(
        self,
        model_id: str,
        device: str | None = None,
        query_prompt: str | None = None,
        query_instruction: str | None = None,
        normalize: bool = True,
    ):
        self.model_id = model_id
        self.device = device
        self.query_prompt = query_prompt
        self.query_instruction = query_instruction
        self.normalize = normalize
        self._model = None

    def name(self) -> str:
        return f"sentence-transformers:{self.model_id}"

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            kwargs = {}
            device = self.device or _auto_device()
            if device:
                kwargs["device"] = device
            self._model = SentenceTransformer(self.model_id, **kwargs)
        return self._model

    def _encode(self, texts, prompt_name: str | None = None, prompt: str | None = None):
        model = self._get_model()
        kwargs = {"normalize_embeddings": self.normalize}
        if prompt_name:
            kwargs["prompt_name"] = prompt_name
        if prompt:
            kwargs["prompt"] = prompt
        embeddings = model.encode(texts, **kwargs)
        return embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings

    def __call__(self, input):
        return self.embed_documents(input)

    def embed_documents(self, input):
        texts = [input] if isinstance(input, str) else list(input or [])
        return self._encode(texts)

    def embed_query(self, input):
        query = input if isinstance(input, str) else (input[0] if input else "")
        if self.query_instruction:
            prompt_text = f"Instruct: {self.query_instruction}\nQuery: {query}"
            return self._encode([prompt_text])
        if self.query_prompt:
            try:
                return self._encode([query], prompt_name=self.query_prompt)
            except Exception:
                return self._encode([query])
        return self._encode([query])

class LMStudioEmbeddingFunction:
    def __init__(
        self,
        base_url: str,
        model: str,
        query_instruction: str | None = None,
        dimensions: int | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.query_instruction = query_instruction
        self.dimensions = dimensions
        self._resolved_model = None

    def name(self) -> str:
        return f"lmstudio:{self._resolve_model()}"

    def __call__(self, input):
        return self.embed_documents(input)

    def embed_documents(self, input):
        texts = [input] if isinstance(input, str) else list(input or [])
        return self._request(texts)

    def embed_query(self, input):
        query = input if isinstance(input, str) else (input[0] if input else "")
        if self.query_instruction:
            query = f"Instruct: {self.query_instruction}\nQuery: {query}"
        return self._request([query])

    def _request(self, texts):
        import httpx
        model = self._resolve_model()
        payload = {"model": model, "input": texts}
        if self.dimensions:
            payload["dimensions"] = self.dimensions
        resp = httpx.post(f"{self.base_url}/embeddings", json=payload, timeout=120.0)
        if resp.status_code == 400:
            fallback = self._pick_model()
            if fallback and fallback != model:
                self._resolved_model = fallback
                self.model = fallback
                payload["model"] = fallback
                resp = httpx.post(f"{self.base_url}/embeddings", json=payload, timeout=120.0)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return [item.get("embedding", []) for item in data]

    def _resolve_model(self) -> str:
        if self._resolved_model:
            return self._resolved_model
        if self.model and self.model != "auto":
            self._resolved_model = self.model
            return self._resolved_model
        picked = self._pick_model()
        if not picked:
            raise RuntimeError("Aucun modele d'embedding disponible dans LM Studio.")
        self._resolved_model = picked
        self.model = picked
        return picked

    def _pick_model(self) -> str | None:
        import httpx
        try:
            resp = httpx.get(f"{self.base_url}/models", timeout=10.0)
            resp.raise_for_status()
        except Exception:
            return None
        data = resp.json().get("data", [])
        candidates = []
        for item in data:
            model_id = str(item.get("id", ""))
            if "embed" in model_id.lower():
                candidates.append(model_id)
        if not candidates:
            return None
        lowered = [(m.lower(), m) for m in candidates]
        for key, original in lowered:
            if "qwen3-embedding" in key:
                return original
        for key, original in lowered:
            if "qwen" in key and "embed" in key:
                return original
        return candidates[0]


_collection = None
_embedding_fn = None

def _auto_device() -> str | None:
    if DEFAULT_EMBED_DEVICE:
        return DEFAULT_EMBED_DEVICE
    try:
        import torch
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        return None
    return None

def _get_embedding_function():
    global _embedding_fn
    if _embedding_fn is not None:
        return _embedding_fn

    backend = (os.environ.get("RAG_EMBED_BACKEND") or DEFAULT_EMBED_BACKEND).strip().lower()
    model_id = (os.environ.get("RAG_EMBED_MODEL") or DEFAULT_EMBED_MODEL).strip()
    query_prompt = (os.environ.get("RAG_EMBED_QUERY_PROMPT") or DEFAULT_QUERY_PROMPT)
    query_instruction = (os.environ.get("RAG_EMBED_QUERY_INSTRUCTION") or DEFAULT_QUERY_INSTRUCTION).strip()
    lmstudio_url = (os.environ.get("RAG_EMBED_LMSTUDIO_URL") or DEFAULT_LMSTUDIO_URL).strip()
    lmstudio_dim = (os.environ.get("RAG_EMBED_LMSTUDIO_DIM") or DEFAULT_LMSTUDIO_DIM).strip()

    if backend in {"sentence-transformers", "st", "qwen3", "hf"}:
        try:
            if model_id == "auto":
                model_id = "Qwen/Qwen3-Embedding-8B"
            _embedding_fn = SentenceTransformerEmbeddingFunction(
                model_id=model_id,
                device=DEFAULT_EMBED_DEVICE,
                query_prompt=query_prompt,
                query_instruction=query_instruction,
            )
            return _embedding_fn
        except Exception:
            _embedding_fn = SimpleEmbeddingFunction()
            return _embedding_fn

    if backend in {"lmstudio", "lm-studio", "lm", "openai"}:
        dim = int(lmstudio_dim) if lmstudio_dim.isdigit() else None
        _embedding_fn = LMStudioEmbeddingFunction(
            base_url=lmstudio_url,
            model=model_id,
            query_instruction=query_instruction,
            dimensions=dim,
        )
        return _embedding_fn

    _embedding_fn = SimpleEmbeddingFunction()
    return _embedding_fn


def _get_collection():
    global _collection
    if chromadb is None:
        return None
    if _collection is not None:
        return _collection
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    _collection = client.get_or_create_collection(
        name=_collection_name(),
        metadata={"hnsw:space": "cosine"},
        embedding_function=_get_embedding_function(),
    )
    return _collection

def _collection_name() -> str:
    embedding_name = _get_embedding_function().name()
    if not embedding_name:
        return COLLECTION_NAME
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", embedding_name)
    if len(safe) > 60:
        safe = safe[:60]
    return f"{COLLECTION_NAME}__{safe}"


def _append_fallback(doc: str, metadata: dict) -> None:
    entry = {"document": doc, "metadata": metadata}
    with open(FALLBACK_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _truncate(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "\n\n[...contenu tronque...]"


def add_conversation_turn(
    role: str,
    content: str,
    source: str = "unknown",
    conversation_id: str = "default",
    metadata: dict | None = None,
) -> str:
    if not content:
        return "Erreur : contenu vide."

    doc = _truncate(f"{role}: {content}")
    embedding_name = _get_embedding_function().name()
    meta = {
        "timestamp": int(time.time()),
        "role": role,
        "source": source,
        "conversation_id": conversation_id or "default",
        "embedding": embedding_name,
    }
    if metadata:
        meta.update(metadata)

    collection = _get_collection()
    if collection is None:
        _append_fallback(doc, meta)
        return "OK (fallback)"

    collection.add(
        ids=[str(uuid.uuid4())],
        documents=[doc],
        metadatas=[meta],
    )
    return "OK"


def search_conversations(
    query: str,
    n_results: int = 5,
    conversation_id: str | None = None,
) -> str:
    if not query:
        return "Erreur : requete vide."

    embedding_name = _get_embedding_function().name()
    collection = _get_collection()
    if collection is None:
        return _search_fallback(query, n_results, conversation_id, embedding_name)

    filters = []
    if conversation_id:
        filters.append({"conversation_id": conversation_id})
    if embedding_name:
        filters.append({"embedding": embedding_name})
    if not filters:
        where = None
    elif len(filters) == 1:
        where = filters[0]
    else:
        where = {"$and": filters}
    res = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    if not docs:
        return "Aucun resultat."

    lines = ["RAG (conversations):"]
    for doc, meta, dist in zip(docs, metas, dists):
        source = meta.get("source", "unknown") if isinstance(meta, dict) else "unknown"
        role = meta.get("role", "?") if isinstance(meta, dict) else "?"
        score = 1.0 - float(dist) if dist is not None else 0.0
        lines.append(f"- [{source}/{role}] score={score:.2f} :: {doc}")
    return "\n".join(lines)


def _search_fallback(
    query: str,
    n_results: int,
    conversation_id: str | None,
    embedding_name: str | None,
) -> str:
    if not os.path.exists(FALLBACK_FILE):
        return "Aucun resultat."

    query_words = set(re.findall(r"[\\w\\-]+", query.lower()))
    scored = []
    with open(FALLBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            doc = entry.get("document", "")
            meta = entry.get("metadata", {})
            if conversation_id and meta.get("conversation_id") != conversation_id:
                continue
            if embedding_name and meta.get("embedding") != embedding_name:
                continue
            doc_words = set(re.findall(r"[\\w\\-]+", doc.lower()))
            score = len(query_words.intersection(doc_words))
            if score > 0:
                scored.append((score, doc, meta))

    if not scored:
        return "Aucun resultat."

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:n_results]

    lines = ["RAG (fallback):"]
    for score, doc, meta in top:
        source = meta.get("source", "unknown")
        role = meta.get("role", "?")
        lines.append(f"- [{source}/{role}] score={score} :: {doc}")
    return "\n".join(lines)
