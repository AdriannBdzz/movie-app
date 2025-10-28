from pydantic import BaseModel
from typing import List, Optional


class Movie(BaseModel):
	id: int
	title: str
	poster_path: Optional[str] = None
	genre_ids: Optional[list[int]] = None


class SearchResponse(BaseModel):
	results: List[Movie]

class FavoriteIn(BaseModel):
	user_id: str
	movie: Movie


class FavoriteOut(Movie):
	pass


class RecoResponse(BaseModel):
	count: int
	results: List[Movie]