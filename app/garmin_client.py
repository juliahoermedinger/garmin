"""Garmin Connect integration.

Uses the `garminconnect` package (an actively-maintained, unofficial wrapper
around Garmin's mobile-app API - there is no accessible public API for hobby
projects). Login happens once per user via email/password, with an MFA
step if Garmin challenges the login; the resulting session token (not the
password) is what gets stored, encrypted, for future syncs.

The MFA handshake is stateful on the `Garmin` client object in memory (the
library does not support serializing "MFA in progress" state), so a pending
login is held in `_pending_mfa` between the "enter password" request and the
"enter MFA code" request. This only works within a single running process -
fine for this app's single-worker deployment model.
"""

import time
from datetime import datetime

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
from sqlalchemy.orm import Session

from .crypto import decrypt_text, encrypt_text
from .models import GarminLink, Run, User, utcnow

_MFA_TTL_SECONDS = 10 * 60
_pending_mfa: dict[int, tuple[float, Garmin]] = {}

_RUNNING_TYPE_HINT = "running"


class GarminLoginError(Exception):
    """Raised for any Garmin auth/connectivity failure that should be shown to the user."""


def start_login(user_id: int, email: str, password: str) -> tuple[bool, str | None]:
    """Begin a Garmin login.

    Returns (mfa_required, token_json). If mfa_required is True, token_json is
    None and the caller must collect a code and call submit_mfa_code(). If
    mfa_required is False, token_json is the session token to persist.
    """
    client = Garmin(email=email, password=password, return_on_mfa=True)
    try:
        mfa_status, _ = client.login()
    except GarminConnectTooManyRequestsError as exc:
        raise GarminLoginError(
            "Garmin is rate-limiting login attempts right now. Wait a few minutes and try again."
        ) from exc
    except GarminConnectAuthenticationError as exc:
        raise GarminLoginError("Garmin rejected that email/password.") from exc
    except GarminConnectConnectionError as exc:
        raise GarminLoginError(f"Could not reach Garmin: {exc}") from exc

    if mfa_status == "needs_mfa":
        _pending_mfa[user_id] = (time.time(), client)
        return True, None

    return False, client.client.dumps()


def submit_mfa_code(user_id: int, code: str) -> str:
    """Complete a pending MFA login. Returns the token JSON to persist."""
    entry = _pending_mfa.pop(user_id, None)
    if entry is None:
        raise GarminLoginError(
            "No Garmin login is waiting for a code (it may have expired) - please start over."
        )
    started_at, client = entry
    if time.time() - started_at > _MFA_TTL_SECONDS:
        raise GarminLoginError("That Garmin login attempt expired - please start over.")

    try:
        client.resume_login(None, code)
    except GarminConnectAuthenticationError as exc:
        raise GarminLoginError("Incorrect code - please start over and reconnect Garmin.") from exc
    except GarminConnectConnectionError as exc:
        raise GarminLoginError(f"Could not complete Garmin login: {exc}") from exc

    return client.client.dumps()


def save_garmin_link(db: Session, user: User, token_json: str) -> None:
    encrypted = encrypt_text(token_json)
    link = user.garmin_link
    if link is None:
        link = GarminLink(user_id=user.id, encrypted_token_blob=encrypted, status="connected")
        db.add(link)
    else:
        link.encrypted_token_blob = encrypted
        link.status = "connected"
    db.commit()


def _parse_activity_start(activity: dict) -> datetime:
    raw = activity.get("startTimeLocal") or activity.get("startTimeGMT")
    if not raw:
        return utcnow().replace(tzinfo=None)
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return utcnow().replace(tzinfo=None)


def sync_runs_for_user(db: Session, user: User, limit: int = 50) -> int:
    """Pull recent running activities from Garmin for this user.

    Returns the number of newly-imported runs. Raises GarminLoginError if the
    stored session is no longer valid (caller should prompt to reconnect).
    """
    link = user.garmin_link
    if link is None:
        raise GarminLoginError("Garmin is not connected for this account yet.")

    token_json = decrypt_text(link.encrypted_token_blob)
    client = Garmin()
    try:
        client.login(tokenstore=token_json)
    except GarminConnectAuthenticationError as exc:
        link.status = "needs_reauth"
        db.commit()
        raise GarminLoginError("Your Garmin session expired - please reconnect Garmin.") from exc
    except GarminConnectConnectionError as exc:
        raise GarminLoginError(f"Could not reach Garmin: {exc}") from exc

    try:
        activities = client.get_activities(0, limit)
    except (GarminConnectConnectionError, GarminConnectTooManyRequestsError) as exc:
        raise GarminLoginError(f"Could not fetch activities from Garmin: {exc}") from exc

    existing_ids = {
        row[0]
        for row in db.query(Run.garmin_activity_id).filter(Run.user_id == user.id).all()
    }

    new_count = 0
    for activity in activities:
        activity_type = activity.get("activityType") or {}
        type_key = (activity_type.get("typeKey") or "").lower()
        if _RUNNING_TYPE_HINT not in type_key:
            continue

        activity_id = str(activity.get("activityId"))
        if activity_id in existing_ids:
            continue

        run = Run(
            user_id=user.id,
            garmin_activity_id=activity_id,
            start_time=_parse_activity_start(activity),
            duration_seconds=activity.get("duration") or 0,
            distance_meters=activity.get("distance") or 0,
            avg_hr=activity.get("averageHR"),
            max_hr=activity.get("maxHR"),
            elevation_gain_m=activity.get("elevationGain"),
            calories=activity.get("calories"),
        )
        db.add(run)
        existing_ids.add(activity_id)
        new_count += 1

    link.encrypted_token_blob = encrypt_text(client.client.dumps())
    link.status = "connected"
    link.last_synced_at = utcnow()
    db.commit()
    return new_count
