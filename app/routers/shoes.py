from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Run, Shoe, User
from ..security import require_user
from ..templating import templates

router = APIRouter(prefix="/shoes")


def _shoe_stats(db: Session, shoe: Shoe) -> dict:
    runs = db.query(Run).filter(Run.shoe_id == shoe.id).all()
    total_distance_km = sum(r.distance_meters for r in runs) / 1000
    return {"shoe": shoe, "run_count": len(runs), "total_distance_km": total_distance_km}


@router.get("")
def list_shoes(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    shoes = db.query(Shoe).filter(Shoe.user_id == user.id).order_by(Shoe.retired, Shoe.name).all()
    shoe_stats = [_shoe_stats(db, shoe) for shoe in shoes]
    return templates.TemplateResponse(
        request,
        "shoes.html",
        {"user": user, "shoe_stats": shoe_stats, "error": request.query_params.get("error")},
    )


@router.post("")
def create_shoe(
    request: Request,
    name: str = Form(...),
    brand: str = Form(""),
    model: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    name = name.strip()
    if not name:
        return RedirectResponse("/shoes?error=Give the shoe a name", status_code=303)
    shoe = Shoe(user_id=user.id, name=name, brand=brand.strip() or None, model=model.strip() or None)
    db.add(shoe)
    db.commit()
    return RedirectResponse("/shoes", status_code=303)


@router.post("/{shoe_id}/retire")
def toggle_retire(shoe_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    shoe = db.query(Shoe).filter(Shoe.id == shoe_id, Shoe.user_id == user.id).first()
    if shoe:
        shoe.retired = not shoe.retired
        db.commit()
    return RedirectResponse("/shoes", status_code=303)


@router.post("/{shoe_id}/delete")
def delete_shoe(shoe_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    shoe = db.query(Shoe).filter(Shoe.id == shoe_id, Shoe.user_id == user.id).first()
    if shoe:
        db.query(Run).filter(Run.shoe_id == shoe.id).update({Run.shoe_id: None})
        db.delete(shoe)
        db.commit()
    return RedirectResponse("/shoes", status_code=303)
