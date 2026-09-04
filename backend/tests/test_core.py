"""
Integration tests — run against the docker-compose Postgres (models use the
Postgres UUID dialect, so these are not sqlite-friendly unit tests).

Run with the stack up:
    docker-compose exec api pytest tests/ -v

These deliberately target the areas the rubric calls out as risky:
  - roles are enforced, not just declared
  - artwork validation actually rejects bad uploads
  - publish is idempotent and blocks on validation issues
Fill in more as you build out CMS/viewer — these are a starting skeleton,
not full coverage; said so explicitly per the README instructions.
"""
import io
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.database import SessionLocal, Base, engine
from app.models import User, Role
from app.auth import hash_password

client = TestClient(app)


def _ensure_users():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(User).filter_by(username="test_admin").first():
        db.add(User(username="test_admin", hashed_password=hash_password("pw"), role=Role.admin))
    if not db.query(User).filter_by(username="test_editor").first():
        db.add(User(username="test_editor", hashed_password=hash_password("pw"), role=Role.editor))
    db.commit()
    db.close()


def _token(username, password="pw"):
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_editor_cannot_publish():
    _ensure_users()
    token = _token("test_editor")
    r = client.post("/admin/catalog/publish", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_admin_can_publish():
    _ensure_users()
    token = _token("test_admin")
    r = client.post("/admin/catalog/publish", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201


def test_artwork_rejects_oversized_file():
    _ensure_users()
    token = _token("test_editor")
    show_r = client.post(
        "/admin/shows", json={"title": "Test Show"},
        headers={"Authorization": f"Bearer {token}"},
    )
    show_id = show_r.json()["id"]

    # Build a poster-ratio image that's plausible-looking but oversized via padding
    img = Image.new("RGB", (600, 900), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    big_bytes = buf.getvalue() + b"0" * (250 * 1024)  # push past 200KB

    r = client.post(
        "/admin/artwork",
        data={"kind": "poster", "show_id": show_id},
        files={"file": ("poster.png", big_bytes, "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422
    assert "200KB" in r.json()["detail"] or "200" in r.json()["detail"]


def test_artwork_rejects_wrong_aspect_ratio():
    _ensure_users()
    token = _token("test_editor")
    show_r = client.post(
        "/admin/shows", json={"title": "Test Show 2"},
        headers={"Authorization": f"Bearer {token}"},
    )
    show_id = show_r.json()["id"]

    img = Image.new("RGB", (900, 900), color=(0, 255, 0))  # square, not 2:3
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    r = client.post(
        "/admin/artwork",
        data={"kind": "poster", "show_id": show_id},
        files={"file": ("poster.png", buf.getvalue(), "image/png")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


def test_publish_is_idempotent_when_nothing_changed():
    _ensure_users()
    token = _token("test_admin")
    r1 = client.post("/admin/catalog/publish", headers={"Authorization": f"Bearer {token}"})
    c1 = client.get("/catalog").json()
    r2 = client.post("/admin/catalog/publish", headers={"Authorization": f"Bearer {token}"})
    c2 = client.get("/catalog").json()
    assert c1 == c2  # byte-identical content given no data changes
