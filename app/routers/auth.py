from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..security import (
    clear_session_cookie,
    get_current_user_optional,
    hash_password,
    set_session_cookie,
    verify_password,
)
from ..templating import templates

router = APIRouter()


@router.get("/register")
def register_form(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "register.html", {"error": request.query_params.get("error")})


@router.post("/register")
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    if not email or "@" not in email:
        return RedirectResponse("/register?error=Enter a valid email address", status_code=303)
    if len(password) < 8:
        return RedirectResponse("/register?error=Password must be at least 8 characters", status_code=303)
    if len(password.encode("utf-8")) > 72:
        return RedirectResponse("/register?error=Password must be at most 72 characters", status_code=303)
    if password != password_confirm:
        return RedirectResponse("/register?error=Passwords do not match", status_code=303)
    if db.query(User).filter(User.email == email).first():
        return RedirectResponse("/register?error=An account with that email already exists", status_code=303)

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)

    response = RedirectResponse("/", status_code=303)
    set_session_cookie(response, user.id)
    return response


@router.get("/login")
def login_form(request: Request, user: User | None = Depends(get_current_user_optional)):
    if user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": request.query_params.get("error")})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        return RedirectResponse("/login?error=Incorrect email or password", status_code=303)

    response = RedirectResponse("/", status_code=303)
    set_session_cookie(response, user.id)
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    clear_session_cookie(response)
    return response
