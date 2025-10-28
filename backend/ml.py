# backend/ml.py
import os
import json
import random
from collections import Counter
import numpy as np

MODELS_DIR = "models"
os.makedirs(MODELS_DIR, exist_ok=True)

# --- Tokenización (misma idea que en app.movie_tokens) ---
def _movie_tokens(m: dict) -> set[str]:
    toks = set()
    for g in m.get("genre_ids") or []:
        toks.add(f"g{g}")
    for k in m.get("keyword_ids") or []:
        toks.add(f"k{k}")
    for d in m.get("director_ids") or []:
        toks.add(f"d{d}")
    cid = m.get("collection_id")
    if cid:
        toks.add(f"c{cid}")
    title = (m.get("title") or "").lower()
    for w in title.replace(":", " ").replace("-", " ").split():
        if len(w) >= 5:
            toks.add(f"t{w}")
    return toks

def _build_vocab(movies: list[dict], max_vocab: int = 2000) -> dict[str, int]:
    cnt = Counter()
    for m in movies:
        cnt.update(_movie_tokens(m))
    most = [t for t, _ in cnt.most_common(max_vocab)]
    return {t: i for i, t in enumerate(most)}

def _vectorize(movies: list[dict], vocab: dict[str, int]) -> np.ndarray:
    X = np.zeros((len(movies), len(vocab)), dtype=np.float32)
    for i, m in enumerate(movies):
        for t in _movie_tokens(m):
            j = vocab.get(t)
            if j is not None:
                X[i, j] = 1.0
    return X

def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))

# ----------------- API pública -----------------

def train_user_model(user_id: str,
                     positives: list[dict],
                     negatives_pool: list[dict],
                     neg_ratio: int = 5,
                     epochs: int = 250,
                     lr: float = 0.2,
                     l2: float = 1e-4,
                     max_vocab: int = 2000) -> None:
    """
    Entrena una regresión logística binaria por usuario:
    - Positivos = favoritos enriquecidos.
    - Negativos = muestra aleatoria de candidatas NO favoritas.
    Guarda pesos y vocabulario en /models.
    """
    # Construir negativos
    neg_pool = [m for m in negatives_pool if m["id"] not in {p["id"] for p in positives}]
    n_pos = len(positives)
    n_neg = min(len(neg_pool), max(n_pos * neg_ratio, 20))
    if n_neg == 0 or n_pos == 0:
        # Datos insuficientes: no entrenamos
        return
    negatives = random.sample(neg_pool, n_neg)

    # Vocabulario y matrices
    vocab = _build_vocab(positives + negatives, max_vocab=max_vocab)
    X_pos = _vectorize(positives, vocab)
    X_neg = _vectorize(negatives, vocab)
    X = np.vstack([X_pos, X_neg])
    y = np.concatenate([np.ones(len(X_pos), dtype=np.float32),
                        np.zeros(len(X_neg), dtype=np.float32)])

    # Entrenamiento por GD
    w = np.zeros(X.shape[1], dtype=np.float32)
    for _ in range(epochs):
        z = X @ w
        p = _sigmoid(z)
        grad = (X.T @ (p - y)) / X.shape[0] + l2 * w
        w -= lr * grad

    # Guardar modelo
    np.save(os.path.join(MODELS_DIR, f"{user_id}_w.npy"), w)
    with open(os.path.join(MODELS_DIR, f"{user_id}_vocab.json"), "w", encoding="utf-8") as f:
        json.dump(vocab, f)

def load_user_model(user_id: str):
    w_path = os.path.join(MODELS_DIR, f"{user_id}_w.npy")
    v_path = os.path.join(MODELS_DIR, f"{user_id}_vocab.json")
    if not (os.path.exists(w_path) and os.path.exists(v_path)):
        return None, None
    w = np.load(w_path)
    with open(v_path, "r", encoding="utf-8") as f:
        vocab = json.load(f)
    return w, vocab

def score_movies_for_user(user_id: str, movies: list[dict]) -> list[float]:
    w, vocab = load_user_model(user_id)
    if w is None or vocab is None or not movies:
        return []
    X = _vectorize(movies, vocab)
    probs = _sigmoid(X @ w)
    return probs.tolist()
