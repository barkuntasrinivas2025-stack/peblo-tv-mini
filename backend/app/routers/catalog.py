import json
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..storage import get_storage
from ..publish import CURRENT_POINTER_KEY

router = APIRouter(tags=["catalog"])


def _load_current_catalogue() -> dict:
    storage = get_storage()
    if not storage.exists(CURRENT_POINTER_KEY):
        raise HTTPException(404, "No catalogue has been published yet.")
    return json.loads(storage.get(CURRENT_POINTER_KEY))


@router.get("/catalog")
def get_catalog():
    """What the viewer UI reads. Never touches the DB — served from the
    published artifact only, which is the whole point of publishing."""
    return _load_current_catalogue()


@router.get("/catalog/search")
def search_catalog(
    q: Optional[str] = None,
    category: Optional[str] = None,
    language: Optional[str] = None,
    section: Optional[str] = None,
):
    catalogue = _load_current_catalogue()
    results = []

    for sec_name, shows in catalogue["sections"].items():
        if section and sec_name != section:
            continue
        for show in shows:
            if category and show.get("category") != category:
                continue

            matched_episodes = []
            for season in show["seasons"]:
                for ep in season["episodes"]:
                    if language and language not in ep["languages"]:
                        continue
                    if q:
                        haystack = " ".join([show["title"], ep["title"], show.get("category") or ""]).lower()
                        if q.lower() not in haystack:
                            continue
                    matched_episodes.append({**ep, "season": season["number"]})

            title_matches_q = (not q) or (q.lower() in show["title"].lower())
            if matched_episodes or (title_matches_q and not language):
                results.append({
                    "show": {"id": show["id"], "title": show["title"], "artwork": show["artwork"]},
                    "section": sec_name,
                    "matched_episodes": matched_episodes,
                })

    return {"count": len(results), "results": results}

# NOTE (see README "Search" section for the honest version of this answer):
# this is O(catalogue size) per request, fine for ~hundreds of shows.
# At real scale this becomes a search index (Postgres full-text / Meilisearch)
# built at publish time, not a per-request scan of the whole JSON blob.
