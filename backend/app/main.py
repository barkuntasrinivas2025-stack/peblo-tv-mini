from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from .database import Base, engine
from .routers import admin, catalog, auth_router

app = FastAPI(title="Peblo TV Mini")

app.include_router(auth_router.router)
app.include_router(admin.router)
app.include_router(catalog.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    """Alert on: DB reachability. This is the one thing that silently
    breaks every other endpoint without an obvious symptom to an editor —
    uploads and publish both fail confusingly if Postgres is unreachable,
    so surfacing it directly here is the highest-value single alert."""
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        db_ok = True
    except OperationalError:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "db_reachable": db_ok}
