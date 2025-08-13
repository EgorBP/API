from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, index=True, nullable=False)
    gif_count = Column(Integer, default=0, nullable=False)


class Gif(Base):
    __tablename__ = 'gifs'

    id = Column(Integer, primary_key=True)
    tg_gif_id = Column(String(255), unique=True, nullable=False)


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    tag = Column(String(100), unique=True, nullable=False)


class UserGifTag(Base):
    __tablename__ = 'user_gif_tags'

    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), primary_key=True)
    gif_id = Column(Integer, ForeignKey('gifs.id', ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey('tags.id', ondelete="CASCADE"), primary_key=True)
