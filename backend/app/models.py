import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Role(str, enum.Enum):
    editor = "editor"
    admin = "admin"


class ArtworkKind(str, enum.Enum):
    poster = "poster"     # 2:3, ~600x900
    banner = "banner"     # 16:9, ~1280x720
    thumbnail = "thumbnail"  # 16:9, ~640x360


class PublishOutcome(str, enum.Enum):
    success = "success"
    failed = "failed"


# --- Auth (deliberately minimal — swap for real IdP in prod) ---
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False, default=Role.editor)


class Show(Base):
    __tablename__ = "shows"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False)
    synopsis = Column(Text, default="")
    section = Column(String, nullable=True)  # required at publish time, not creation
    category = Column(String, nullable=True)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    seasons = relationship("Season", back_populates="show", cascade="all, delete-orphan")
    artworks = relationship("Artwork", back_populates="show", cascade="all, delete-orphan")


class Season(Base):
    __tablename__ = "seasons"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    show_id = Column(UUID(as_uuid=False), ForeignKey("shows.id"), nullable=False)
    number = Column(Integer, nullable=False)  # 0 reserved for trailers

    show = relationship("Show", back_populates="seasons")
    episodes = relationship("Episode", back_populates="season", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("show_id", "number", name="uq_show_season_number"),)


class Episode(Base):
    __tablename__ = "episodes"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    season_id = Column(UUID(as_uuid=False), ForeignKey("seasons.id"), nullable=False)
    title = Column(String, nullable=False)
    language = Column(String, nullable=False)
    content_group = Column(String, nullable=False)  # groups language variants of same episode
    duration_seconds = Column(Integer, nullable=True)  # required at publish time
    order_index = Column(Integer, default=0)
    is_published = Column(Boolean, default=False)

    season = relationship("Season", back_populates="episodes")
    artworks = relationship("Artwork", back_populates="episode", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("content_group", "language", name="uq_content_group_language"),
    )


class Artwork(Base):
    __tablename__ = "artworks"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    kind = Column(Enum(ArtworkKind), nullable=False)
    storage_key = Column(String, nullable=False)  # abstraction: opaque key, not a path
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    size_bytes = Column(Integer, nullable=False)

    show_id = Column(UUID(as_uuid=False), ForeignKey("shows.id"), nullable=True)
    episode_id = Column(UUID(as_uuid=False), ForeignKey("episodes.id"), nullable=True)

    show = relationship("Show", back_populates="artworks")
    episode = relationship("Episode", back_populates="artworks")


class PublishRun(Base):
    __tablename__ = "publish_runs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    triggered_by = Column(String, nullable=False)  # username
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    outcome = Column(Enum(PublishOutcome), nullable=True)
    shows_count = Column(Integer, default=0)
    episodes_count = Column(Integer, default=0)
    catalogue_key = Column(String, nullable=True)  # storage key of the version written
    error = Column(Text, nullable=True)
    meta = Column(JSON, default=dict)
