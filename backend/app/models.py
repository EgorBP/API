from enum import Enum

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Common declarative base class for all ORM models in the project."""


class User(Base):
    """A registered user, identified by their Telegram account.

    Attributes:
        id: Internal primary key.
        tg_id: Telegram user ID. Unique and indexed, used to look up or
            create the corresponding internal `id` on first contact.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    tg_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True,     # If delete it alembic can create useless migration. But now in database exist only one index 
        nullable=False
    )


class UserStatus(str, Enum):
    """Cached user existence state, used as a Redis value.

    Attributes:
        ACTIVE: The user exists in the database.
        DELETED_OR_NOT_FOUND: The user does not exist, either because
            they were deleted or never existed.
    """
    ACTIVE = "active"
    DELETED_OR_NOT_FOUND = "deleted_or_not_found"


class Gif(Base):
    """A single GIF or MP4 file stored on disk (or another storage app).

    A `Gif` row is shared across all users who have it in their library;
    per-user tagging is tracked separately via `UserGifTag`.

    Attributes:
        id: Internal primary key.
        file_path: Path to the file, relative to `settings.BASE_DIR`.
            Unique.
        file_hash: SHA-256 hash of the file contents, used to detect and
            reuse already-uploaded files. Unique.
    """
    __tablename__ = "gifs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    file_path: Mapped[str] = mapped_column(
        String(),
        unique=True,
        nullable=False
    )

    file_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False
    )


class Tag(Base):
    """A single tag that can be attached to a GIF by a user.

    Tags are global and deduplicated: the same tag string is shared across
    all users and GIFs rather than duplicated per owner.

    Attributes:
        id: Internal primary key.
        tag: The tag's text value. Unique, up to 100 characters.
    """
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    tag: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )


class UserGifTag(Base):
    """Association between a user, a GIF, and one tag they assigned it.

    Represents a single `(user, gif, tag)` combination. A GIF tagged by a
    user with three tags produces three rows here — one per tag — all
    sharing the same `user_id`/`gif_id` pair.

    Attributes:
        user_id: FK to `users.id`. Cascades on delete.
        gif_id: FK to `gifs.id`. Cascades on delete.
        tag_id: FK to `tags.id`. Cascades on delete.
        user: The associated `User`.
        gif: The associated `Gif`.
        tag: The associated `Tag`.
    """
    __tablename__ = "user_gif_tags"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )

    gif_id: Mapped[int] = mapped_column(
        ForeignKey("gifs.id", ondelete="CASCADE"),
        primary_key=True
    )

    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True
    )

    user: Mapped["User"] = relationship()
    gif: Mapped["Gif"] = relationship()
    tag: Mapped["Tag"] = relationship()
