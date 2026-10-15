"""Sign in, sign out, and who am I. There is no sign-up page: create users with

uv run python -m app.auth.create_user <username>
"""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.auth import service
from app.auth.deps import CurrentUser
from app.auth.models import LoginRequest, UserPublic
from app.db import DbSession

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserPublic)
def login(data: LoginRequest, request: Request, session: DbSession):
    user = service.authenticate(session, data.username, data.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong username or password")
    request.session.clear()
    request.session["user_id"] = user.id
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request):
    request.session.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserPublic)
def current_user(user: CurrentUser):
    return user
