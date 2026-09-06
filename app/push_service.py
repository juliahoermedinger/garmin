"""Sends Web Push notifications to a user's subscribed browsers/devices."""

import json
import logging

from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from .config import PUSH_ENABLED, VAPID_CONTACT_EMAIL, VAPID_PRIVATE_KEY
from .models import PushSubscription, User

logger = logging.getLogger(__name__)


def notify_user(db: Session, user: User, title: str, body: str, url: str = "/runs") -> None:
    if not PUSH_ENABLED:
        return

    subscriptions = db.query(PushSubscription).filter(PushSubscription.user_id == user.id).all()
    if not subscriptions:
        return

    payload = json.dumps({"title": title, "body": body, "url": url})

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{VAPID_CONTACT_EMAIL}"},
            )
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                # The browser/OS says this subscription is gone for good - stop trying it.
                db.delete(sub)
            else:
                logger.warning("Push notification failed for user %s: %s", user.email, exc)
        except Exception as exc:  # network errors, malformed endpoints, etc.
            logger.warning("Push notification failed for user %s: %s", user.email, exc)

    db.commit()
