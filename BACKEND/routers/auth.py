from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from auth import verify_password, create_token, get_current_user

router = APIRouter(tags=["Authentication"])


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.execute(
        text("SELECT email, name, password_hash, role FROM users WHERE email = :email"),
        {"email": form_data.username}
    ).fetchone()

    if not user or not verify_password(form_data.password, user[2]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_token({"sub": user[0], "name": user[1], "role": user[3]})
    return {
        "access_token": token,
        "token_type":   "bearer",
        "name":         user[1],
        "email":        user[0],
        "role":         user[3],
    }


@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    return current_user