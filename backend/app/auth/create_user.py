"""Create a user (or reset their password) from the command line:

uv run python -m app.auth.create_user <username> [--name "Display Name"]
"""

import argparse
import getpass

from sqlmodel import Session

from app.auth import service
from app.config import get_settings
from app.db import create_db_engine
from app.db.migrate import run_migrations


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a FieldOps user, or reset their password.")
    parser.add_argument("username")
    parser.add_argument("--name", default="", help="display name (defaults to the username)")
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    if not password or password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords are empty or don't match.")

    engine = create_db_engine(get_settings())
    try:
        run_migrations(engine)
        with Session(engine) as session:
            user = service.get_user_by_username(session, args.username)
            if user is None:
                user = service.create_user(session, args.username, password, args.name)
                action = "Created"
            else:
                user.password_hash = service.hash_password(password)
                if args.name:
                    user.display_name = args.name
                session.add(user)
                action = "Updated"
            session.commit()
            print(f"{action} user {user.username!r}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
