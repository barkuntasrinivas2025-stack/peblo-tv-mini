from datetime import datetime

from pydantic import BaseModel, Field

from .models import ArtworkKind, PublishOutcome, Role


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
    duration_seconds: int | None = None
    order_index: int = 0


class EpisodeOut(EpisodeIn):
    id: str
    is_published: bool
    artworks: list[ArtworkOut] = []

    class Config:
        from_attributes = True


class SeasonIn(BaseModel):
    number: int = Field(ge=0)


class SeasonOut(SeasonIn):
    id: str
    episodes: list[EpisodeOut] = []

    class Config:
        from_attributes = True


class ShowIn(BaseModel):
    title: str
    synopsis: str = ""
    section: str | None = None
    category: str | None = None


class ShowOut(ShowIn):
    id: str
    is_published: bool
    created_at: datetime
    seasons: list[SeasonOut] = []
    artworks: list[ArtworkOut] = []

    class Config:
        from_attributes = True


class ValidationIssue(BaseModel):
    entity_type: str  # "show" | "episode"
    entity_id: str
    entity_title: str
    reason: str        # human-readable, editor-actionable


class ValidationReport(BaseModel):
    blocking_issue_count: int
    issues: list[ValidationIssue]


class PublishRunOut(BaseModel):
    id: str
    triggered_by: str
    started_at: datetime
    finished_at: datetime | None
    outcome: PublishOutcome | None
    shows_count: int
    episodes_count: int
    catalogue_key: str | None
    error: str | None

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    username: str
    role: Role
