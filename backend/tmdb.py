import os
import requests
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_LANG = os.getenv("TMDB_LANG", "es-ES")
TMDB_REGION = os.getenv("TMDB_REGION", "ES")
TMDB_BASE = "https://api.themoviedb.org/3"

if not TMDB_API_KEY:
    raise RuntimeError("TMDB_API_KEY no está configurada. Copia .env.example a .env y edita tu clave.")

session = requests.Session()


def search_movies(query: str):
    url = f"{TMDB_BASE}/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "include_adult": False,
        "language": TMDB_LANG,
        "region": TMDB_REGION,
        "page": 1,
    }
    r = session.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    results = []
    for m in data.get("results", []):
        results.append({
            "id": m["id"],
            "title": m.get("title") or m.get("name"),
            "poster_path": m.get("poster_path"),
            "genre_ids": m.get("genre_ids", []),
        })
    return results


def popular_movies(page: int = 1):
    url = f"{TMDB_BASE}/movie/popular"
    params = {
        "api_key": TMDB_API_KEY,
        "language": TMDB_LANG,
        "region": TMDB_REGION,
        "page": page,
    }
    r = session.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    results = []
    for m in data.get("results", []):
        results.append({
            "id": m["id"],
            "title": m.get("title"),
            "poster_path": m.get("poster_path"),
            "genre_ids": m.get("genre_ids", []),
        })
    return results


def movie_details(movie_id: int):
    """Detalles básicos para asegurar genre_ids."""
    url = f"{TMDB_BASE}/movie/{movie_id}"
    params = {"api_key": TMDB_API_KEY, "language": TMDB_LANG}
    r = session.get(url, params=params, timeout=20)
    r.raise_for_status()
    m = r.json()
    return {
        "id": m["id"],
        "title": m.get("title"),
        "poster_path": m.get("poster_path"),
        "genre_ids": [g["id"] for g in m.get("genres", [])],
    }


def discover_by_genres(genre_ids: list[int], page: int = 1):
    """Candidatas usando géneros del usuario (incluye voto)."""
    url = f"{TMDB_BASE}/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "language": TMDB_LANG,
        "region": TMDB_REGION,
        "include_adult": False,
        "sort_by": "popularity.desc",
        "with_genres": ",".join(map(str, genre_ids)) if genre_ids else "",
        "page": page,
    }
    r = session.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    results = []
    for m in data.get("results", []):
        results.append({
            "id": m["id"],
            "title": m.get("title"),
            "poster_path": m.get("poster_path"),
            "genre_ids": m.get("genre_ids", []),
            "vote_average": m.get("vote_average", 0.0),
            "vote_count": m.get("vote_count", 0),
        })
    return results


def movie_enriched(movie_id: int):
    """Detalles enriquecidos: géneros, keywords, directores y colección + voto."""
    url = f"{TMDB_BASE}/movie/{movie_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": TMDB_LANG,
        "append_to_response": "keywords,credits",
    }
    r = session.get(url, params=params, timeout=20)
    r.raise_for_status()
    m = r.json()

    genres = [g["id"] for g in m.get("genres", [])]

    kw_container = m.get("keywords", {})
    if isinstance(kw_container, dict):
        keyword_ids = [k["id"] for k in kw_container.get("keywords", [])]
    elif isinstance(kw_container, list):
        keyword_ids = [k["id"] for k in kw_container]
    else:
        keyword_ids = []

    directors = []
    credits = m.get("credits", {})
    for crew in credits.get("crew", []) or []:
        if crew.get("job") == "Director":
            directors.append(crew["id"])

    collection_id = None
    col = m.get("belongs_to_collection")
    if isinstance(col, dict):
        collection_id = col.get("id")

    return {
        "id": m["id"],
        "title": m.get("title"),
        "poster_path": m.get("poster_path"),
        "genre_ids": genres,
        "keyword_ids": keyword_ids,
        "director_ids": directors,
        "collection_id": collection_id,
        "vote_average": m.get("vote_average", 0.0),
        "vote_count": m.get("vote_count", 0),
    }


def collection_movies(collection_id: int):
    """Películas de una colección/franquicia (incluye voto)."""
    if not collection_id:
        return []
    url = f"{TMDB_BASE}/collection/{collection_id}"
    params = {"api_key": TMDB_API_KEY, "language": TMDB_LANG}
    r = session.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    out = []
    for m in data.get("parts", []):
        out.append({
            "id": m["id"],
            "title": m.get("title"),
            "poster_path": m.get("poster_path"),
            "genre_ids": m.get("genre_ids", []),
            "vote_average": m.get("vote_average", 0.0),
            "vote_count": m.get("vote_count", 0),
        })
    return out


def discover_by_keywords(keyword_ids: list[int], page: int = 1):
    """Candidatas por palabras clave (temas/personajes/franquicias) con voto."""
    if not keyword_ids:
        return []
    url = f"{TMDB_BASE}/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "language": TMDB_LANG,
        "region": TMDB_REGION,
        "include_adult": False,
        "sort_by": "popularity.desc",
        "with_keywords": ",".join(map(str, keyword_ids)),
        "page": page,
    }
    r = session.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    results = []
    for m in data.get("results", []):
        results.append({
            "id": m["id"],
            "title": m.get("title"),
            "poster_path": m.get("poster_path"),
            "genre_ids": m.get("genre_ids", []),
            "vote_average": m.get("vote_average", 0.0),
            "vote_count": m.get("vote_count", 0),
        })
    return results


def person_directed_movies(person_id: int):
    """Filmografía como director (incluye voto)."""
    url = f"{TMDB_BASE}/person/{person_id}/movie_credits"
    params = {"api_key": TMDB_API_KEY, "language": TMDB_LANG}
    r = session.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    out = []
    for c in data.get("crew", []):
        if c.get("job") == "Director":
            out.append({
                "id": c["id"],
                "title": c.get("title"),
                "poster_path": c.get("poster_path"),
                "genre_ids": c.get("genre_ids", []),
                "vote_average": c.get("vote_average", 0.0),
                "vote_count": c.get("vote_count", 0),
            })
    return out
