import time

from fastapi import Depends, FastAPI, Request, Response
from prometheus_client import Histogram, make_asgi_app
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import __version__
from .config import settings
from .db import get_session
from .routes import invitations, orgs

REQUESTS = Histogram("eightguard_http_request_duration_seconds", "HTTP request latency", ["method", "route", "status"])

app = FastAPI(title="EightGuard API", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json")
app.mount("/metrics", make_asgi_app())


@app.middleware("http")
async def observe(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    if route is not None:
        REQUESTS.labels(request.method, route.path, response.status_code).observe(time.perf_counter() - start)
    response.headers["Cache-Control"] = "no-store"  # API responses carry tenant data
    return response


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz(response: Response, session: Session = Depends(get_session)):
    try:
        session.execute(text("SELECT 1"))
        return {"postgres": "ok"}
    except Exception:
        response.status_code = 503
        return {"postgres": "down"}


@app.get("/api/version")
def version():
    return {"version": settings.version or __version__}


app.include_router(orgs.router)
app.include_router(invitations.router)
