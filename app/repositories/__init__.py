"""Data-access layer: one repository per ORM model, all built on `_BaseRepository`."""

from .base import _BaseRepository
from .user import UserRepository
from .gif import GifRepository
from .tag import TagRepository
from .user_gif_tag import UserGifTagRepository
