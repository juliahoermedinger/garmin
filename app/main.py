from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401 - import registers models on Base before create_all
from .database import Base, engine
from .routers import auth, dashboard, garmin, push, runs, shoes
from .scheduler import start_scheduler, stop_scheduler
from .security import AuthRequired

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Running Tracker")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(AuthRequired)
def auth_required_handler(request: Request, exc: AuthRequired):
    return RedirectResponse("/login", status_code=303)


@app.get("/sw.js")
def service_worker():
    # Served from the root (not /static/sw.js) so its default scope covers the
    # whole site - a service worker's push/notificationclick handlers only see
    # pages under wherever the script itself was served from.
    return FileResponse("app/static/sw.js", media_type="application/javascript")


@app.on_event("startup")
def on_startup():
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(shoes.router)
app.include_router(runs.router)
app.include_router(garmin.router)
app.include_router(push.router)
