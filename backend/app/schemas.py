from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from .models import Role, ArtworkKind, PublishOutcome


class ArtworkOut(BaseModel):
    id: str
    kind: ArtworkKind
    storage_key: str
    width: int
    height: int
    size_bytes: int

    class Config:
        from_attributes = True


class EpisodeIn(BaseModel):
    title: str
    language: str
    content_group: str
    duration_seconds: Optional[int] = None
    order_index: int = 0


class EpisodeOut(EpisodeIn):
    id: str
    is_published: bool
    artworks: List[ArtworkOut] = []

    class Config:
        from_attributes = True


class SeasonIn(BaseModel):
    number: int = Field(ge=0)


class SeasonOut(SeasonIn):
    id: str
    episodes: List[EpisodeOut] = []

    class Config:
        from_attributes = True


class ShowIn(BaseModel):
    title: str
    synopsis: str = ""
    section: Optional[str] = None
    category: Optional[str] = None


class ShowOut(ShowIn):
    id: str
    is_published: bool
    created_at: datetime
    seasons: List[SeasonOut] = []
    artworks: List[ArtworkOut] = []

    class Config:
        from_attributes = True


class ValidationIssue(BaseModel):
    entity_type: str  # "show" | "episode"
    entity_id: str
    entity_title: str
    reason: str        # human-readable, editor-actionable


class ValidationReport(BaseModel):
    blocking_issue_count: int
    issues: List[ValidationIssue]


class PublishRunOut(BaseModel):
    id: str
    triggered_by: str
    started_at: datetime
    finished_at: Optional[datetime]
    outcome: Optional[PublishOutcome]
    shows_count: int
    episodes_count: int
    catalogue_key: Optional[str]
    error: Optional[str]

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    username: str
    role: Role
