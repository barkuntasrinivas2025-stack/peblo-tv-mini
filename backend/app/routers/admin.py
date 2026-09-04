import io
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..auth import require_admin, require_editor
from ..database import get_db
from ..models import Artwork, ArtworkKind, Episode, Season, Show, User
from ..publish import build_validation_report, run_publish
from ..schemas import (
    ArtworkOut,
    EpisodeIn,
    EpisodeOut,
    PublishRunOut,
    SeasonIn,
    SeasonOut,
    ShowIn,
    ShowOut,
    ValidationReport,
)
from ..storage import get_storage

router = APIRouter(prefix="/admin", tags=["admin"])

# Specs — in a real system these come from reference.json / config, not hardcoded.
ARTWORK_SPECS = {
    ArtworkKind.poster: {
        "ratio": (2, 3),
        "target": (600, 900),
        "tolerance_pct": 5,
    },
    ArtworkKind.banner: {
        "ratio": (16, 9),
        "target": (1280, 720),
        "tolerance_pct": 5,
    },
    ArtworkKind.thumbnail: {
        "ratio": (16, 9),
        "target": (640, 360),
        "tolerance_pct": 5,
    },
}

MAX_ARTWORK_BYTES = 200 * 1024  # 200 KB ceiling


# ---------- Shows ----------


@router.get("/shows", response_model=list[ShowOut])
def list_shows(
    q: str | None = None,
    section: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_editor),
):
    query = db.query(Show).options(
        joinedload(Show.seasons).joinedload(Season.episodes),
        joinedload(Show.artworks),
    )

    if q:
        query = query.filter(Show.title.ilike(f"%{q}%"))

    if section:
        query = query.filter(Show.section == section)

    return query.all()


@router.post("/shows", response_model=ShowOut, status_code=201)
def create_show(
    payload: ShowIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_editor),
):
    show = Show(**payload.model_dump())

    db.add(show)
    db.commit()
    db.refresh(show)

    return show


@router.patch("/shows/{show_id}", response_model=ShowOut)
def update_show(
    show_id: str,
    payload: ShowIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_editor),
):
    show = db.query(Show).get(show_id)

    if not show:
        raise HTTPException(404, "Show not found")

    for key, value in payload.model_dump().items():
        setattr(show, key, value)

    db.commit()
    db.refresh(show)

    return show


@router.post("/shows/{show_id}/publish-flag", response_model=ShowOut)
def set_show_publish_flag(
    show_id: str,
    published: bool,
    db: Session = Depends(get_db),
    _user: User = Depends(require_editor),
):
    """Marks intent to publish; actual catalogue publish is a separate admin-only action."""

    show = db.query(Show).get(show_id)

    if not show:
        raise HTTPException(404, "Show not found")

    if published and not show.section:
        raise HTTPException(
            422,
            "A published show must have a section.",
        )

    show.is_published = published

    db.commit()
    db.refresh(show)

    return show


# ---------- Seasons / Episodes ----------


@router.post(
    "/shows/{show_id}/seasons",
    response_model=SeasonOut,
    status_code=201,
)
def create_season(
    show_id: str,
    payload: SeasonIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_editor),
):
    show = db.query(Show).get(show_id)

    if not show:
        raise HTTPException(404, "Show not found")

    season = Season(
        show_id=show_id,
        **payload.model_dump(),
    )

    db.add(season)
    db.commit()
    db.refresh(season)

    return season


@router.post(
    "/seasons/{season_id}/episodes",
    response_model=EpisodeOut,
    status_code=201,
)
def create_episode(
    season_id: str,
    payload: EpisodeIn,
    db: Session = Depends(get_db),
    _user: User = Depends(require_editor),
):
    season = db.query(Season).get(season_id)

    if not season:
        raise HTTPException(404, "Season not found")

    episode = Episode(
        season_id=season_id,
        **payload.model_dump(),
    )

    db.add(episode)

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            409,
            (
                f"(content_group='{payload.content_group}', "
                f"language='{payload.language}') already exists."
            ),
        )

    db.refresh(episode)

    return episode


@router.post(
    "/episodes/{episode_id}/publish-flag",
    response_model=EpisodeOut,
)
def set_episode_publish_flag(
    episode_id: str,
    published: bool,
    db: Session = Depends(get_db),
    _user: User = Depends(require_editor),
):
    ep = db.query(Episode).get(episode_id)

    if not ep:
        raise HTTPException(404, "Episode not found")

    if published:
        if not ep.duration_seconds:
            raise HTTPException(
                422,
                "Cannot publish an episode with no duration.",
            )

        if not ep.artworks and not ep.season.show.artworks:
            raise HTTPException(
                422,
                "Cannot publish an episode with no artwork.",
            )

    ep.is_published = published

    db.commit()
    db.refresh(ep)

    return ep


# ---------- Artwork upload ----------


def _validate_dimensions(
    kind: ArtworkKind,
    width: int,
    height: int,
) -> str | None:
    spec = ARTWORK_SPECS[kind]

    target_width, target_height = spec["target"]
    tolerance = spec["tolerance_pct"] / 100

    width_valid = (
        target_width * (1 - tolerance)
        <= width
        <= target_width * (1 + tolerance)
    )

    height_valid = (
        target_height * (1 - tolerance)
        <= height
        <= target_height * (1 + tolerance)
    )

    if not width_valid or not height_valid:
        return (
            f"{kind.value} must be about "
            f"{target_width}x{target_height}px "
            f"(±{spec['tolerance_pct']}%). "
            f"Got {width}x{height}px. "
            "Please re-export at the correct size."
        )

    ratio_width, ratio_height = spec["ratio"]

    actual_ratio = width / height
    expected_ratio = ratio_width / ratio_height

    if abs(actual_ratio - expected_ratio) > 0.03:
        return (
            f"{kind.value} must be "
            f"{ratio_width}:{ratio_height}. "
            f"Got a {width}:{height} image — "
            "that's the wrong aspect ratio."
        )

    return None


@router.post(
    "/artwork",
    response_model=ArtworkOut,
    status_code=201,
)
async def upload_artwork(
    kind: ArtworkKind = Form(...),
    show_id: str | None = Form(None),
    episode_id: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_editor),
):
    if not show_id and not episode_id:
        raise HTTPException(
            422,
            "Provide either show_id or episode_id.",
        )

    raw = await file.read()

    if len(raw) > MAX_ARTWORK_BYTES:
        raise HTTPException(
            422,
            (
                f"File is {len(raw) // 1024}KB — "
                "the limit is 200KB. "
                "Please compress the image before re-uploading."
            ),
        )

    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()

        img = Image.open(io.BytesIO(raw))
        width, height = img.size

    except (UnidentifiedImageError, OSError):
        raise HTTPException(
            422,
            (
                "That file isn't a readable image. "
                "Please upload a JPG or PNG."
            ),
        )

    err = _validate_dimensions(
        kind,
        width,
        height,
    )

    if err:
        raise HTTPException(422, err)

    extension = (
        (file.filename or "jpg")
        .split(".")[-1]
        .lower()
    )

    key = (
        f"artwork/{kind.value}/"
        f"{uuid.uuid4()}.{extension}"
    )

    get_storage().put(
        key,
        raw,
    )

    artwork = Artwork(
        kind=kind,
        storage_key=key,
        width=width,
        height=height,
        size_bytes=len(raw),
        show_id=show_id,
        episode_id=episode_id,
    )

    db.add(artwork)
    db.commit()
    db.refresh(artwork)

    return artwork


# ---------- Publish ----------


@router.get(
    "/validation-report",
    response_model=ValidationReport,
)
def validation_report(
    db: Session = Depends(get_db),
    _user: User = Depends(require_editor),
):
    return build_validation_report(db)


@router.post(
    "/catalog/publish",
    response_model=PublishRunOut,
    status_code=201,
)
def publish_catalog(
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    return run_publish(
        db,
        triggered_by=user.username,
    )


@router.get(
    "/catalog/publish-runs",
    response_model=list[PublishRunOut],
)
def publish_run_history(
    db: Session = Depends(get_db),
    _user: User = Depends(require_editor),
):
    from ..models import PublishRun

    return (
        db.query(PublishRun)
        .order_by(PublishRun.started_at.desc())
        .limit(50)
        .all()
    )
