from enum import Enum
from sqlalchemy import String, Integer, BigInteger, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
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
    ACTIVE = "active"
    BANNED = "banned"
    DELETED_OR_NOT_FOUND = "deleted_or_not_found"


class Gif(Base):
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
