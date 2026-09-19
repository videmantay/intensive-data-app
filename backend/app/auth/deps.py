"""`CurrentUser`: the signed-in user, or a 401.

The login endpoint stores `user_id` in Starlette's signed session cookie. Routers
included in app/main.py with `dependencies=[Depends(require_user)]` reject anonymous
requests; endpoints that need to know *who* is asking take a `CurrentUser` parameter.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.auth import service
from app.auth.models import User
from app.db import DbSession


def require_user(request: Request, session: DbSession) -> User:
    user_id = request.session.get("user_id")
    user = service.get_user(session, user_id) if isinstance(user_id, int) else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user


CurrentUser = Annotated[User, Depends(require_user)]
