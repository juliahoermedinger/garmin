import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .config import SYNC_INTERVAL_MINUTES
from .database import SessionLocal
from .garmin_client import GarminLoginError, sync_runs_for_user
from .models import User

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def sync_all_users() -> None:
    db = SessionLocal()
    try:
        users = db.query(User).join(User.garmin_link).all()
        for user in users:
            if user.garmin_link is None or user.garmin_link.status != "connected":
                continue
            try:
                new_count = sync_runs_for_user(db, user)
                if new_count:
                    logger.info("Synced %d new run(s) for user %s", new_count, user.email)
            except GarminLoginError as exc:
                logger.warning("Background sync failed for user %s: %s", user.email, exc)
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        sync_all_users,
        "interval",
        minutes=SYNC_INTERVAL_MINUTES,
        id="sync_all_users",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
