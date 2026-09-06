from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..config import PUSH_ENABLED, VAPID_PUBLIC_KEY
from ..database import get_db
from ..models import PushSubscription, User
from ..security import require_user

router = APIRouter(prefix="/push")


@router.get("/public-key")
def public_key():
    if not PUSH_ENABLED:
        return JSONResponse({"error": "Push notifications are not configured on this server."}, status_code=404)
    return {"publicKey": VAPID_PUBLIC_KEY}


@router.post("/subscribe")
async def subscribe(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    if not PUSH_ENABLED:
        return JSONResponse({"error": "Push notifications are not configured on this server."}, status_code=404)

    body = await request.json()
    endpoint = body.get("endpoint")
    keys = body.get("keys") or {}
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")
    if not endpoint or not p256dh or not auth:
        return JSONResponse({"error": "Malformed subscription."}, status_code=400)

    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    if existing:
        existing.user_id = user.id
        existing.p256dh = p256dh
        existing.auth = auth
    else:
        db.add(PushSubscription(user_id=user.id, endpoint=endpoint, p256dh=p256dh, auth=auth))
    db.commit()
    return {"ok": True}


@router.post("/unsubscribe")
async def unsubscribe(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    body = await request.json()
    endpoint = body.get("endpoint")
    db.query(PushSubscription).filter(
        PushSubscription.endpoint == endpoint, PushSubscription.user_id == user.id
    ).delete()
    db.commit()
    return {"ok": True}
