from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Run, Shoe, User
from ..security import require_user
from ..templating import templates

router = APIRouter(prefix="/runs")


@router.get("")
def list_runs(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    runs = db.query(Run).filter(Run.user_id == user.id).order_by(Run.start_time.desc()).all()
    shoes = (
        db.query(Shoe)
        .filter(Shoe.user_id == user.id, Shoe.retired == False)  # noqa: E712
        .order_by(Shoe.name)
        .all()
    )
    return templates.TemplateResponse(
        request,
        "runs_list.html",
        {"user": user, "runs": runs, "shoes": shoes, "msg": request.query_params.get("msg")},
    )


@router.get("/{run_id}")
def run_detail(request: Request, run_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id, Run.user_id == user.id).first()
    if run is None:
        return RedirectResponse("/runs", status_code=303)
    shoes = db.query(Shoe).filter(Shoe.user_id == user.id).order_by(Shoe.retired, Shoe.name).all()
    return templates.TemplateResponse(request, "run_detail.html", {"user": user, "run": run, "shoes": shoes})


@router.post("/{run_id}/shoe")
def assign_shoe(
    request: Request,
    run_id: int,
    shoe_id: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    run = db.query(Run).filter(Run.id == run_id, Run.user_id == user.id).first()
    if run is not None:
        if shoe_id:
            shoe = db.query(Shoe).filter(Shoe.id == int(shoe_id), Shoe.user_id == user.id).first()
            run.shoe_id = shoe.id if shoe else None
        else:
            run.shoe_id = None
        db.commit()

    referer = request.headers.get("referer", "/runs")
    return RedirectResponse(referer, status_code=303)
