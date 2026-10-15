"""`CurrentUser`: whoever the request belongs to.

**Login is bypassed for the demo.** A request with no session falls back to a built-in
demo user, so every page works without signing in. The sign-in endpoints still work, and
a request that *is* signed in is treated as that user, so ownership is still enforced
everywhere (dashboards, widgets, chat threads).

To require real logins again: make `require_user` raise 401 instead of returning
`demo_user(session)` (git history has the original), and restore the login page and route
guard in the frontend (`src/routes/login.tsx`, `src/routes/__root.tsx`).
"""

from typing import Annotated

from fastapi import Depends, Request

from app.auth import service
from app.auth.models import User
from app.db import DbSession


def require_user(request: Request, session: DbSession) -> User:
    user_id = request.session.get("user_id")
    user = service.get_user(session, user_id) if isinstance(user_id, int) else None
    return user if user is not None else service.demo_user(session)


CurrentUser = Annotated[User, Depends(require_user)]
