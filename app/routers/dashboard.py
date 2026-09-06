from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Run, Shoe, User, utcnow
from ..security import require_user
from ..templating import templates

router = APIRouter()


@router.get("/")
def dashboard(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    runs = db.query(Run).filter(Run.user_id == user.id).order_by(Run.start_time.desc()).all()

    now = utcnow().replace(tzinfo=None)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    week_runs = [r for r in runs if r.start_time >= week_ago]
    month_runs = [r for r in runs if r.start_time >= month_ago]

    def totals(run_list):
        return {
            "count": len(run_list),
            "distance_km": sum(r.distance_meters for r in run_list) / 1000,
            "duration_hours": sum(r.duration_seconds for r in run_list) / 3600,
        }

    shoes = db.query(Shoe).filter(Shoe.user_id == user.id).all()
    shoe_mileage = []
    for shoe in shoes:
        km = sum(r.distance_meters for r in runs if r.shoe_id == shoe.id) / 1000
        if km > 0 or not shoe.retired:
            shoe_mileage.append({"name": shoe.name, "km": round(km, 1)})

    recent = list(reversed(runs[:15]))
    trend = {
        "labels": [r.start_time.strftime("%b %d") for r in recent],
        "avg_hr": [r.avg_hr for r in recent],
        "pace_min_per_km": [
            round(r.avg_pace_per_km / 60, 2) if r.avg_pace_per_km else None for r in recent
        ],
    }

    unassigned_count = sum(1 for r in runs if r.shoe_id is None)

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": user,
            "week": totals(week_runs),
            "month": totals(month_runs),
            "shoe_mileage": shoe_mileage,
            "trend": trend,
            "run_count": len(runs),
            "unassigned_count": unassigned_count,
            "garmin_connected": user.garmin_link is not None and user.garmin_link.status == "connected",
        },
    )
