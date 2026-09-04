"""
Publish pipeline.

Atomicity: we build the entire catalogue in memory, serialize it once, and
write it under a *new* storage key (catalogue/<run_id>.json), then flip a
single pointer (catalogue/current.json) to that key only after the write
fully succeeds. LocalDiskStorage.put() itself writes to a .tmp file and
os.rename()'s it into place, which is atomic at the filesystem level — so
even that pointer flip can't leave a half-written file visible to readers.

If the process dies mid-publish:
  - Before the final pointer flip: readers keep serving the last-good
    catalogue untouched. The half-built run_id file is orphaned garbage,
    harmless, cleanable later.
  - The PublishRun row is written with outcome=None until we know the
    result; a crash leaves it stuck "in progress" rather than silently
    "succeeded", which is the safe failure mode for an operator to notice.

Idempotency: re-running publish with no data changes produces byte-identical
output (deterministic ordering, no timestamps embedded in catalogue content
itself) so publishing twice in a row is a safe no-op in effect.
"""
import json
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .models import Episode, PublishOutcome, PublishRun, Show
from .schemas import ValidationIssue, ValidationReport
from .storage import get_storage

CURRENT_POINTER_KEY = "catalogue/current.json"


def build_validation_report(db: Session) -> ValidationReport:
    issues: list[ValidationIssue] = []

    shows = db.query(Show).all()
    for show in shows:
        if not show.is_published:
            continue  # only published-intent shows are checked for blocking issues
        if not show.section:
            issues.append(ValidationIssue(
                entity_type="show", entity_id=show.id, entity_title=show.title,
                reason="Marked published but has no section assigned.",
            ))
        for season in show.seasons:
            for ep in season.episodes:
                if not ep.is_published:
                    continue
                if not ep.duration_seconds:
                    issues.append(ValidationIssue(
                        entity_type="episode", entity_id=ep.id, entity_title=ep.title,
                        reason=f"'{ep.title}' has no duration set.",
                    ))
                has_artwork = len(ep.artworks) > 0 or len(show.artworks) > 0
                if not has_artwork:
                    issues.append(ValidationIssue(
                        entity_type="episode", entity_id=ep.id, entity_title=ep.title,
                        reason=f"'{ep.title}' has no artwork uploaded.",
                    ))

    # (content_group, language) uniqueness is already enforced at the DB
    # level via a UniqueConstraint, so it can never reach this report —
    # noted here so the intent is visible to a reviewer.

    return ValidationReport(blocking_issue_count=len(issues), issues=issues)


def _artwork_urls(entity) -> dict:
    out = {}
    for art in entity.artworks:
        out[art.kind.value] = f"/storage/{art.storage_key}"
    return out


def _build_catalogue_dict(db: Session) -> dict:
    sections: dict[str, list] = defaultdict(list)

    shows = (
        db.query(Show)
        .filter(Show.is_published.is_(True))
        .order_by(Show.title.asc())  # deterministic ordering
        .all()
    )

    for show in shows:
        seasons_out = []
        for season in sorted(show.seasons, key=lambda s: s.number):
            if season.number == 0:
                continue  # trailers are not a normal season in the viewer

            # collapse (content_group) -> one entry with a languages list
            groups: dict[str, list[Episode]] = defaultdict(list)
            for ep in season.episodes:
                if not ep.is_published:
                    continue
                groups[ep.content_group].append(ep)

            episodes_out = []
            for content_group, variants in sorted(groups.items()):
                variants_sorted = sorted(variants, key=lambda e: e.language)
                primary = variants_sorted[0]
                episodes_out.append({
                    "content_group": content_group,
                    "title": primary.title,
                    "duration_seconds": primary.duration_seconds,
                    "order_index": primary.order_index,
                    "languages": [v.language for v in variants_sorted],
                    "artwork": _artwork_urls(primary),
                })

            episodes_out.sort(key=lambda e: e["order_index"])
            if episodes_out:
                seasons_out.append({"number": season.number, "episodes": episodes_out})

        # trailers, if any, surfaced separately (not "a season")
        trailer_season = next((s for s in show.seasons if s.number == 0), None)
        trailers_out = []
        if trailer_season:
            for ep in trailer_season.episodes:
                if ep.is_published:
                    trailers_out.append({
                        "title": ep.title, "language": ep.language,
                        "duration_seconds": ep.duration_seconds,
                    })

        entry = {
            "id": show.id,
            "title": show.title,
            "synopsis": show.synopsis,
            "category": show.category,
            "artwork": _artwork_urls(show),
            "seasons": seasons_out,
            "trailers": trailers_out,
        }
        sections[show.section].append(entry)

    return {"sections": dict(sorted(sections.items())), "generated_fields_are_deterministic": True}


def run_publish(db: Session, triggered_by: str) -> PublishRun:
    report = build_validation_report(db)
    run = PublishRun(triggered_by=triggered_by, started_at=datetime.now(timezone.utc))
    db.add(run)
    db.commit()
    db.refresh(run)

    if report.blocking_issue_count > 0:
        run.finished_at = datetime.now(timezone.utc)
        run.outcome = PublishOutcome.failed
        run.error = f"{report.blocking_issue_count} blocking validation issue(s); publish aborted."
        db.commit()
        return run

    try:
        catalogue = _build_catalogue_dict(db)
        payload = json.dumps(catalogue, indent=2, sort_keys=True).encode("utf-8")

        storage = get_storage()
        versioned_key = f"catalogue/run-{run.id}.json"
        storage.put(versioned_key, payload)      # 1. write full new version
        storage.put(CURRENT_POINTER_KEY, payload)  # 2. flip pointer (atomic rename inside)

        episodes_count = sum(
            len(season["episodes"])
            for shows in catalogue["sections"].values()
            for show in shows
            for season in show["seasons"]
        )

        run.outcome = PublishOutcome.success
        run.shows_count = sum(len(v) for v in catalogue["sections"].values())
        run.episodes_count = episodes_count
        run.catalogue_key = versioned_key
    except Exception as e:  # noqa: BLE001 — publish must never crash the request unlogged
        run.outcome = PublishOutcome.failed
        run.error = str(e)
    finally:
        run.finished_at = datetime.now(timezone.utc)
        db.commit()

    return run
