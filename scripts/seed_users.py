"""Seed users from JSON. Run: uv run python scripts/seed_users.py [--user '{"email":"x","password":"y"}'] [--file path/to/extra.json]"""

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import async_session_maker
from src.cruds.authentication import AuthenticationCrud

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SEED_PATH = os.path.join(SCRIPT_DIR, "seed_data", "users.json")


def load_users_from_json(path: str) -> list[dict]:
    """Load user list from JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return [data]
    return data


def parse_user_arg(value: str) -> dict:
    """Parse --user JSON string."""
    return json.loads(value)


async def seed_users(
    default_path: str = DEFAULT_SEED_PATH,
    extra_users: list[dict] | None = None,
    extra_file: str | None = None,
) -> None:
    """Seed users from default JSON and optional extra sources."""
    authentication_crud = AuthenticationCrud()
    all_users: list[dict] = []

    # Default seed
    if os.path.isfile(default_path):
        all_users.extend(load_users_from_json(default_path))
        print(f"Loaded {len(all_users)} default user(s) from {default_path}")
    else:
        print(f"Default seed file not found: {default_path}")

    # Extra file
    if extra_file and os.path.isfile(extra_file):
        extra = load_users_from_json(extra_file)
        all_users.extend(extra)
        print(f"Loaded {len(extra)} user(s) from {extra_file}")

    # Extra users from CLI
    if extra_users:
        all_users.extend(extra_users)
        print(f"Adding {len(extra_users)} user(s) from CLI")

    if not all_users:
        print("No users to seed.")
        return

    async with async_session_maker() as session:
        for user_data in all_users:
            email = user_data.get("email")
            password = user_data.get("password")

            if not email or not password:
                print(f"Skipping invalid user: {user_data}")
                continue

            existing = await authentication_crud.get(
                session, email=email, is_deleted=False
            )
            if existing:
                user = existing
                print(f"User {email} already exists, skipping create.")
            else:
                try:
                    user = await authentication_crud.create(
                        session, {"email": email, "password": password}
                    )
                    print(f"Created user: {email}")
                except ValueError as e:
                    print(f"Failed to create {email}: {e}")
                    continue

                try:
                    await authentication_crud.update(
                        session, user.id, {"is_deleted": False}
                    )
                    print(f"  Updated user: {email}")
                except ValueError as e:
                    print(f"  Failed to update user: {e}")
                    continue

    print("Seed completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed users from JSON")
    parser.add_argument(
        "--user",
        type=str,
        action="append",
        help='Add user as JSON, e.g. --user \'{"email":"a@b.com","password":"Pass123!"}\'',
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Path to extra JSON file with users array",
    )
    parser.add_argument(
        "--default-path",
        type=str,
        default=DEFAULT_SEED_PATH,
        help=f"Path to default seed JSON (default: {DEFAULT_SEED_PATH})",
    )
    args = parser.parse_args()

    extra_users: list[dict] = []
    if args.user:
        for u in args.user:
            try:
                extra_users.append(parse_user_arg(u))
            except json.JSONDecodeError as e:
                print(f"Invalid --user JSON: {e}")
                sys.exit(1)

    asyncio.run(
        seed_users(
            default_path=args.default_path,
            extra_users=extra_users if extra_users else None,
            extra_file=args.file,
        )
    )
