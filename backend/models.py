from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    movie_id = Column(Integer, index=True)
    movie_title = Column(String)
    poster_path = Column(String, nullable=True)
    genre_ids = Column(String, nullable=True) # coma-separado, p.ej. "28,12"


    __table_args__ = (
        UniqueConstraint('user_id', 'movie_id', name='uq_user_movie'),
    )