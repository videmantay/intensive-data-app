"""Users and password checks."""

import secrets

from pwdlib import PasswordHash
from sqlmodel import Session, select

from app.auth.models import User

_hasher = PasswordHash.recommended()  # argon2

# Verified against when the username doesn't exist, so a wrong username takes as long
# as a wrong password and response times don't reveal which usernames exist.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def get_user(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.exec(select(User).where(User.username == username.strip().lower())).first()


def create_user(session: Session, username: str, password: str, display_name: str = "") -> User:
    username = username.strip().lower()
    user = User(username=username, display_name=display_name or username, password_hash=hash_password(password))
    session.add(user)
    session.flush()
    return user


DEMO_USERNAME = "demo"


def demo_user(session: Session) -> User:
    """The user anonymous requests act as while login is bypassed (see deps.py).

    Created on first use with a random password, so nobody can sign in as it.
    """
    user = get_user_by_username(session, DEMO_USERNAME)
    if user is None:
        user = create_user(session, DEMO_USERNAME, secrets.token_urlsafe(32), "Demo user")
    return user


def authenticate(session: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(session, username)
    if user is None:
        _hasher.verify(password, _DUMMY_HASH)
        return None
    if not _hasher.verify(password, user.password_hash):
        return None
    return user
