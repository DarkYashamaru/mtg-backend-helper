from __future__ import annotations

import argparse
import base64
import binascii
import getpass
import hashlib
import hmac
import secrets


ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000
SALT_BYTES = 16
HASH_BYTES = 32


class InvalidPasswordHash(ValueError):
    """Raised when a stored password hash is malformed or unsupported."""


def _encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


def hash_password(password: str) -> str:
    """Create a versioned password hash suitable for storing in the database."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must be a non-empty string.")

    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS,
        dklen=HASH_BYTES,
    )

    return f"{ALGORITHM}${ITERATIONS}${_encode(salt)}${_encode(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Return True when password matches stored_hash."""
    if not isinstance(password, str):
        return False

    try:
        algorithm, iterations_text, salt_text, digest_text = stored_hash.split("$", 3)
        if algorithm != ALGORITHM:
            raise InvalidPasswordHash(f"Unsupported password hash algorithm: {algorithm}")

        iterations = int(iterations_text)
        salt = _decode(salt_text)
        expected_digest = _decode(digest_text)
    except (AttributeError, TypeError, ValueError, binascii.Error) as exc:
        raise InvalidPasswordHash("Stored password hash is invalid.") from exc

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=len(expected_digest),
    )

    return hmac.compare_digest(actual_digest, expected_digest)


def password_hash_needs_update(stored_hash: str) -> bool:
    """Return True when a hash uses lower security settings than the current defaults."""
    try:
        algorithm, iterations_text, _, _ = stored_hash.split("$", 3)
        return algorithm != ALGORITHM or int(iterations_text) < ITERATIONS
    except (AttributeError, TypeError, ValueError):
        return True


def _read_password(prompt: str) -> str:
    return getpass.getpass(prompt)


def main() -> int:
    parser = argparse.ArgumentParser(description="Hash or verify user passwords.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    hash_parser = subparsers.add_parser("hash", help="Hash a password.")
    hash_parser.add_argument("--password", help="Password to hash. Omit for hidden input.")

    verify_parser = subparsers.add_parser("verify", help="Verify a password against a hash.")
    verify_parser.add_argument("stored_hash", help="Stored password hash.")
    verify_parser.add_argument("--password", help="Password to verify. Omit for hidden input.")

    args = parser.parse_args()

    if args.command == "hash":
        password = args.password or _read_password("Password: ")
        print(hash_password(password))
        return 0

    if args.command == "verify":
        password = args.password or _read_password("Password: ")
        try:
            matches = verify_password(password, args.stored_hash)
        except InvalidPasswordHash as exc:
            parser.error(str(exc))

        print("match" if matches else "no match")
        return 0 if matches else 1

    parser.error("Unsupported command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
