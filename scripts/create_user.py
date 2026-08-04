from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path


def _is_backend_root(path: Path) -> bool:
    return (
        (path / "app" / "main.py").exists()
        and (path / "database" / "session.py").exists()
        and (path / "services" / "users.py").exists()
    )


def _candidate_roots(script_path: Path) -> list[Path]:
    candidates: list[Path] = []

    env_root = os.environ.get("MAGIC_BACKEND_ROOT")
    if env_root:
        candidates.append(Path(env_root).expanduser().resolve())

    candidates.append(Path.cwd().resolve())
    candidates.extend(parent.resolve() for parent in script_path.parents)

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique_candidates.append(candidate)

    return unique_candidates


def resolve_backend_root(script_path: Path, explicit_root: str | None) -> Path:
    if explicit_root:
        root = Path(explicit_root).expanduser().resolve()
        if not _is_backend_root(root):
            raise SystemExit(f"Invalid backend root: {root}")
        return root

    for candidate in _candidate_roots(script_path):
        if _is_backend_root(candidate):
            return candidate

    raise SystemExit(
        "Could not locate the backend root. Pass --backend-root or set MAGIC_BACKEND_ROOT."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a backend user with the same validation and password hashing as the API."
    )
    parser.add_argument("username", help="Username to create.")
    parser.add_argument(
        "--password",
        help="Password to assign. Omit to enter it securely.",
    )
    parser.add_argument(
        "--admin",
        action="store_true",
        help="Create the user with admin privileges.",
    )
    parser.add_argument(
        "--backend-root",
        help="Path to the backend repository root. Optional if MAGIC_BACKEND_ROOT is set or the script is inside the repo tree.",
    )
    return parser.parse_args()


def read_password(password: str | None) -> str:
    if password is not None:
        return password

    first = getpass.getpass("Password: ")
    second = getpass.getpass("Confirm password: ")
    if first != second:
        raise SystemExit("Passwords do not match.")
    return first


def main() -> int:
    args = parse_args()
    script_path = Path(__file__).resolve()
    backend_root = resolve_backend_root(script_path, args.backend_root)

    sys.path.insert(0, str(backend_root))

    from database.create_database import create_database
    from database.session import session_scope
    from services.users import InvalidUserData, UserAlreadyExists, create_user

    password = read_password(args.password)

    create_database()

    try:
        with session_scope() as db:
            user = create_user(
                db,
                args.username,
                password,
                is_admin=args.admin,
                commit=False,
            )
    except InvalidUserData as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except UserAlreadyExists as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Created user '{user.username}' (id={user.id}, admin={'yes' if user.is_admin else 'no'})."
    )
    print(f"Database: {backend_root / 'data.sqlite'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
