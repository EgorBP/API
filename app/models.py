from sqlalchemy import String, Integer, BigInteger, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
        index=True,
        nullable=False
    )


class Gif(Base):
    __tablename__ = "gifs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    tg_gif_id: Mapped[str] = mapped_column(
        String(255),
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
