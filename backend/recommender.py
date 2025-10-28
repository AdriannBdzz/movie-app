from typing import List, Dict
import numpy as np


# Recomendador content-based muy simple:
# Representa cada película por su vector de géneros (one-hot sobre el conjunto de géneros observado en favoritos+populares)
# y puntúa por similitud coseno con el vector promedio de los favoritos del usuario.
# Esto está alineado con la idea de "representación vectorial + similitud" (conceptos base del curso de Andrew Ng).




def build_genre_space(movie_lists: List[List[Dict]]):
	genres = set()
	for lst in movie_lists:
		for m in lst:
			for g in m.get("genre_ids", []) or []:
				genres.add(g)
	genres = sorted(list(genres))
	index = {g: i for i, g in enumerate(genres)}
	return genres, index




def movie_to_vec(m: Dict, index):
	v = np.zeros(len(index), dtype=float)
	for g in (m.get("genre_ids") or []):
		if g in index:
			v[index[g]] = 1.0
	return v




def user_profile(favorites: List[Dict], index):
	if not favorites:
		return None
	vecs = [movie_to_vec(m, index) for m in favorites]
	if not vecs:
		return None
	u = np.mean(np.stack(vecs, axis=0), axis=0)
	# normalizar
	norm = np.linalg.norm(u)
	if norm > 0:
		u = u / norm
	return u




def cosine(a, b):
	na = np.linalg.norm(a)
	nb = np.linalg.norm(b)
	if na == 0 or nb == 0:
		return 0.0
	return float(np.dot(a, b) / (na * nb))




def rank_candidates(favorites: List[Dict], candidates: List[Dict]):
	genres, index = build_genre_space([favorites, candidates])
	u = user_profile(favorites, index)
	if u is None:
		return []
	scored = []
	fav_ids = {m["id"] for m in favorites}
	for c in candidates:
		if c["id"] in fav_ids:
			continue
		v = movie_to_vec(c, index)
		s = cosine(u, v)
		scored.append((s, c))
	scored.sort(key=lambda x: x[0], reverse=True)
	return [c for s, c in scored]