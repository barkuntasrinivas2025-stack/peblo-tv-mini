"""Run with: python -m app.seed
Creates one admin and one editor login, plus one demo show, so
docker-compose up gives you something to click on immediately.
Replace/extend with real seed_shows.json import once you have that file —
see README for where that loader plugs in.
"""
from .database import SessionLocal, Base, engine
from .models import User, Role, Show, Season, Episode
from .auth import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if not db.query(User).filter_by(username="admin").first():
    db.add(User(username="admin", hashed_password=hash_password("admin123"), role=Role.admin))
if not db.query(User).filter_by(username="editor").first():
    db.add(User(username="editor", hashed_password=hash_password("editor123"), role=Role.editor))
db.commit()

if not db.query(Show).filter_by(title="Moti's Many Lives").first():
    show = Show(title="Moti's Many Lives", synopsis="A curious dog explores India's history.",
                section="featured", category="stories")
    db.add(show)
    db.commit()
    db.refresh(show)

    season1 = Season(show_id=show.id, number=1)
    db.add(season1)
    db.commit()
    db.refresh(season1)

    db.add_all([
        Episode(season_id=season1.id, title="The Great Escape", language="en",
                content_group="ep1", duration_seconds=420, order_index=1),
        Episode(season_id=season1.id, title="The Great Escape", language="hi",
                content_group="ep1", duration_seconds=420, order_index=1),
    ])
    db.commit()

print("Seed complete. Login: admin/admin123 or editor/editor123")
db.close()
