# backend/app.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from collections import Counter, defaultdict
import os

from database import Base, engine, get_db
from models import Favorite
from schemas import SearchResponse, FavoriteIn, FavoriteOut, RecoResponse, Movie
from tmdb import (
    search_movies,
    popular_movies,
    movie_details,
    discover_by_genres,
    movie_enriched,
    collection_movies,
    discover_by_keywords,
    person_directed_movies,
)
from ml import train_user_model, load_user_model, score_movies_for_user

# Parámetros de control para diversidad y ranking
MAX_PER_COLLECTION_CANDIDATES = 3   # cuántas cogemos por saga como candidatas
MAX_PER_COLLECTION_FINAL = 2        # cuántas pueden aparecer en el top final
MIN_VOTE_COUNT_FOR_RATING = 150     # ignora notas con pocos votos
RATING_WEIGHT = 0.15                # peso del rating TMDb en el score final
ML_WEIGHT = 0.85                    # peso del modelo ML en el score final

os.makedirs("models", exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Movie Recommender API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def no_cache(request, call_next):
    response = await call_next(request)
    if request.url.path in ("/recommendations", "/favorites", "/search"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response

@app.get("/health")
async def health():
    return {"ok": True, "build": "ml-logreg-v2-retrain"}

@app.get("/search", response_model=SearchResponse)
async def search(q: str):
    if not q or len(q) < 2:
        raise HTTPException(status_code=400, detail="Consulta demasiado corta")
    results = search_movies(q)
    return {"results": results}

# ---------- Helper: reentrenar tras añadir favorito ----------
def _retrain_after_favorite(user_id: str, db: Session):
    """Reentrena el modelo del usuario si ya tiene ≥5 favoritos."""
    fav_rows = db.query(Favorite).filter(Favorite.user_id == user_id).all()
    if len(fav_rows) < 5:
        return

    # Enriquecer favoritos (positivos)
    favs = []
    for f in fav_rows:
        try:
            favs.append(movie_enriched(f.movie_id))
        except Exception:
            favs.append({
                "id": f.movie_id,
                "title": f.movie_title,
                "poster_path": f.poster_path,
                "genre_ids": [int(x) for x in (f.genre_ids or '').split(',') if x],
                "keyword_ids": [],
                "director_ids": [],
                "collection_id": None,
                "vote_average": 0.0,
                "vote_count": 0,
            })

    # Negativos: candidatas por géneros principales + populares
    genre_counts = Counter(g for m in favs for g in (m.get("genre_ids") or []))
    top_genres = [g for g, _ in genre_counts.most_common(3)]

    candidates = []
    if top_genres:
        for p in (1, 2):
            candidates.extend(discover_by_genres(top_genres, page=p))
    candidates.extend(popular_movies(page=1))

    # Deduplicar y quitar favoritas
    fav_ids = {m["id"] for m in favs}
    seen = set()
    negatives_pool = []
    for c in candidates:
        cid = c["id"]
        if cid in fav_ids or cid in seen:
            continue
        seen.add(cid)
        negatives_pool.append(c)

    # Entrenar (se guarda en /models)
    train_user_model(user_id, positives=favs, negatives_pool=negatives_pool)

# ---------- Favoritos CRUD ----------

@app.post("/favorites", response_model=FavoriteOut)
async def add_favorite(payload: FavoriteIn, db: Session = Depends(get_db)):
    # Garantiza genre_ids: si no vienen, los obtenemos de TMDb
    genres = payload.movie.genre_ids or []
    if not genres:
        try:
            details = movie_details(payload.movie.id)
            genres = details.get("genre_ids") or []
        except Exception:
            genres = []

    f = Favorite(
        user_id=payload.user_id,
        movie_id=payload.movie.id,
        movie_title=payload.movie.title,
        poster_path=payload.movie.poster_path,
        genre_ids=",".join(map(str, genres)),
    )

    # evitar duplicados (con backfill si faltaban datos)
    existing = db.query(Favorite).filter(
        Favorite.user_id == f.user_id,
        Favorite.movie_id == f.movie_id
    ).first()
    if existing:
        updated = False
        if (not existing.genre_ids or not existing.genre_ids.strip()) and genres:
            existing.genre_ids = ",".join(map(str, genres))
            updated = True
        if not existing.poster_path and payload.movie.poster_path:
            existing.poster_path = payload.movie.poster_path
            updated = True
        if payload.movie.title and payload.movie.title != existing.movie_title:
            existing.movie_title = payload.movie.title
            updated = True
        if updated:
            db.commit()
            db.refresh(existing)

        # Reentrenar si ya hay suficientes favoritos
        _retrain_after_favorite(payload.user_id, db)

        return Movie(
            id=existing.movie_id,
            title=existing.movie_title,
            poster_path=existing.poster_path,
            genre_ids=[int(x) for x in (existing.genre_ids or '').split(',') if x]
        )

    db.add(f)
    db.commit()
    db.refresh(f)

    # Reentrenar si ya hay suficientes favoritos
    _retrain_after_favorite(payload.user_id, db)

    return Movie(
        id=f.movie_id,
        title=f.movie_title,
        poster_path=f.poster_path,
        genre_ids=[int(x) for x in (f.genre_ids or '').split(',') if x]
    )

@app.get("/favorites", response_model=list[FavoriteOut])
async def list_favorites(user_id: str, db: Session = Depends(get_db)):
    rows = db.query(Favorite).filter(Favorite.user_id == user_id).all()
    out = []
    for r in rows:
        out.append(Movie(
            id=r.movie_id,
            title=r.movie_title,
            poster_path=r.poster_path,
            genre_ids=[int(x) for x in (r.genre_ids or '').split(',') if x]
        ))
    return out

@app.delete("/favorites/{movie_id}")
async def delete_favorite(movie_id: int, user_id: str, db: Session = Depends(get_db)):
    row = db.query(Favorite).filter(Favorite.user_id == user_id, Favorite.movie_id == movie_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(row)
    db.commit()
    return {"deleted": True}

# ----------------- Recomendaciones con ML + diversidad -----------------

@app.get("/recommendations", response_model=RecoResponse)
async def recommendations(user_id: str, db: Session = Depends(get_db)):
    # Favoritos del usuario
    fav_rows = db.query(Favorite).filter(Favorite.user_id == user_id).all()
    if len(fav_rows) < 5:
        raise HTTPException(status_code=400, detail="Necesitas al menos 5 favoritos para ver recomendaciones")

    # Enriquecer favoritos (géneros + keywords + directores + colección + voto)
    favs = []
    for f in fav_rows:
        try:
            enriched = movie_enriched(f.movie_id)
        except Exception:
            enriched = {
                "id": f.movie_id,
                "title": f.movie_title,
                "poster_path": f.poster_path,
                "genre_ids": [int(x) for x in (f.genre_ids or '').split(',') if x],
                "keyword_ids": [],
                "director_ids": [],
                "collection_id": None,
                "vote_average": 0.0,
                "vote_count": 0,
            }
        favs.append(enriched)

    # Señales del usuario
    genre_counts = Counter(g for m in favs for g in (m.get("genre_ids") or []))
    keyword_counts = Counter(k for m in favs for k in (m.get("keyword_ids") or []))
    director_counts = Counter(d for m in favs for d in (m.get("director_ids") or []))
    collections = [m.get("collection_id") for m in favs if m.get("collection_id")]

    top_genres = [g for g, _ in genre_counts.most_common(3)]
    top_keywords = [k for k, _ in keyword_counts.most_common(3)]
    top_directors = [d for d, _ in director_counts.most_common(3)]
    top_collections = list(dict.fromkeys(collections))  # orden estable sin duplicados

    # Candidatas (colección > director > keywords > género) con límite por saga
    candidates = []
    fav_ids_set = {f.movie_id for f in fav_rows}

    # Colecciones: mejor valoradas y límite por saga
    for cid in top_collections:
        coll = collection_movies(cid)
        coll = [m for m in coll if m["id"] not in fav_ids_set]
        coll = sorted(
            coll,
            key=lambda m: ((m.get("vote_average") or 0.0), (m.get("vote_count") or 0)),
            reverse=True
        )
        candidates.extend(coll[:MAX_PER_COLLECTION_CANDIDATES])

    # Directores
    for d in top_directors:
        movies = person_directed_movies(d)
        movies = [m for m in movies if m["id"] not in fav_ids_set]
        candidates.extend(movies)

    # Keywords
    if top_keywords:
        for p in (1, 2):
            kws = discover_by_keywords(top_keywords, page=p)
            kws = [m for m in kws if m["id"] not in fav_ids_set]
            candidates.extend(kws)

    # Géneros
    if top_genres:
        for p in (1, 2):
            gens = discover_by_genres(top_genres, page=p)
            gens = [m for m in gens if m["id"] not in fav_ids_set]
            candidates.extend(gens)

    if not candidates:
        candidates.extend(popular_movies())

    # Deduplicar
    seen = set()
    unique = []
    for c in candidates:
        cid = c["id"]
        if cid in seen or cid in fav_ids_set:
            continue
        seen.add(cid)
        unique.append(c)

    # Enriquecer un subconjunto de candidatas (para features y voto)
    to_enrich = unique[:60]  # aumenta si quieres más señal
    enriched_candidates = []
    for c in to_enrich:
        try:
            e = movie_enriched(c["id"])
            if e.get("vote_average") is None:
                e["vote_average"] = c.get("vote_average", 0.0)
            if e.get("vote_count") is None:
                e["vote_count"] = c.get("vote_count", 0)
            enriched_candidates.append(e)
        except Exception:
            enriched_candidates.append({
                "id": c["id"],
                "title": c.get("title"),
                "poster_path": c.get("poster_path"),
                "genre_ids": c.get("genre_ids", []),
                "keyword_ids": [],
                "director_ids": [],
                "collection_id": None,
                "vote_average": c.get("vote_average", 0.0),
                "vote_count": c.get("vote_count", 0),
            })

    # ML: entrenar si no hay modelo del usuario, luego puntuar candidatas
    w, vocab = load_user_model(user_id)
    if w is None or vocab is None:
        train_user_model(user_id, positives=favs, negatives_pool=enriched_candidates)
    ml_scores = score_movies_for_user(user_id, enriched_candidates)
    if not ml_scores or len(ml_scores) != len(enriched_candidates):
        ml_scores = [0.0] * len(enriched_candidates)

    # Ranking: ML + boost por rating; diversidad por colección
    scored = []
    for c, ml in zip(enriched_candidates, ml_scores):
        rating = float(c.get("vote_average") or 0.0)
        votes = int(c.get("vote_count") or 0)
        rating_norm = (rating / 10.0) if votes >= MIN_VOTE_COUNT_FOR_RATING else 0.0
        final = ML_WEIGHT * ml + (1.0 - ML_WEIGHT) * rating_norm
        scored.append((final, c))

    scored.sort(key=lambda x: x[0], reverse=True)

    per_collection = defaultdict(int)
    top = []
    for s, c in scored:
        col = c.get("collection_id")
        if col and per_collection[col] >= MAX_PER_COLLECTION_FINAL:
            continue
        if col:
            per_collection[col] += 1
        top.append(c)
        if len(top) >= 20:
            break

    return {"count": len(top), "results": top}
