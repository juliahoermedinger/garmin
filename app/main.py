from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401 - import registers models on Base before create_all
from .database import Base, engine
from .routers import auth, dashboard, garmin, runs, shoes
from .scheduler import start_scheduler, stop_scheduler
from .security import AuthRequired

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Running Tracker")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(AuthRequired)
def auth_required_handler(request: Request, exc: AuthRequired):
    return RedirectResponse("/login", status_code=303)


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
