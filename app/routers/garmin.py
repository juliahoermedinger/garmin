from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..garmin_client import GarminLoginError, save_garmin_link, start_login, submit_mfa_code, sync_runs_for_user
from ..models import User
from ..security import require_user
from ..templating import templates

router = APIRouter(prefix="/garmin")


@router.get("/settings")
def settings(request: Request, user: User = Depends(require_user)):
    return templates.TemplateResponse(
        request,
        "garmin_settings.html",
        {
            "user": user,
            "link": user.garmin_link,
            "error": request.query_params.get("error"),
            "msg": request.query_params.get("msg"),
            "awaiting_mfa": request.query_params.get("awaiting_mfa") == "1",
        },
    )


@router.post("/connect")
def connect(
    email: str = Form(...),
    password: str = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    try:
        mfa_required, token_json = start_login(user.id, email.strip(), password)
    except GarminLoginError as exc:
        return RedirectResponse(f"/garmin/settings?error={exc}", status_code=303)

    if mfa_required:
        return RedirectResponse("/garmin/settings?awaiting_mfa=1", status_code=303)

    save_garmin_link(db, user, token_json)
    return RedirectResponse("/garmin/settings?msg=Garmin connected", status_code=303)


@router.post("/mfa")
def mfa(
    code: str = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    try:
        token_json = submit_mfa_code(user.id, code.strip())
    except GarminLoginError as exc:
        return RedirectResponse(f"/garmin/settings?error={exc}", status_code=303)

    save_garmin_link(db, user, token_json)
    return RedirectResponse("/garmin/settings?msg=Garmin connected", status_code=303)


@router.post("/sync")
def sync_now(user: User = Depends(require_user), db: Session = Depends(get_db)):
    try:
        new_count = sync_runs_for_user(db, user)
    except GarminLoginError as exc:
        return RedirectResponse(f"/garmin/settings?error={exc}", status_code=303)

    return RedirectResponse(f"/runs?msg=Synced, {new_count} new run(s)", status_code=303)


@router.post("/disconnect")
def disconnect(user: User = Depends(require_user), db: Session = Depends(get_db)):
    if user.garmin_link is not None:
        db.delete(user.garmin_link)
        db.commit()
    return RedirectResponse("/garmin/settings?msg=Garmin disconnected", status_code=303)
