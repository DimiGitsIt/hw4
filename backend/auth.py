"""Account creation, login, sessions, and password hashing for Campus Customs.

Password storage: new and re-hashed passwords use bcrypt (salted, slow,
industry standard). The three seed users in the database were created with
a legacy scheme (pbkdf2_sha256, 120,000 iterations, hardcoded iteration
count not stored in the hash string) — `_verify_legacy_pbkdf2` only *reads*
that format to let them log in, and a successful legacy login immediately
re-hashes the password with bcrypt and overwrites the stored hash, so the
legacy scheme is never written again.

Sessions: an httpOnly, signed cookie (itsdangerous) containing just the
user id and an expiry, checked on every request. No server-side session
store is needed, and client-side JS (including the chat widget) can never
read the cookie's contents.
"""

import hashlib
import hmac
import re
import secrets
import sqlite3
from pathlib import Path
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
DB_PATH = PROJECT_ROOT / "data" / "campus_customs.db"
ENV_PATH = PROJECT_ROOT / ".env"

SESSION_COOKIE_NAME = "cc_session"
SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 days

LEGACY_PBKDF2_ITERATIONS = 120_000
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
MIN_PASSWORD_LENGTH = 8


def _get_or_create_secret_key() -> str:
    key_name = "SESSION_SECRET_KEY"
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key_name}="):
                value = line.split("=", 1)[1].strip()
                if value:
                    return value
    new_key = secrets.token_hex(32)
    with ENV_PATH.open("a", encoding="utf-8") as f:
        f.write(f"\n{key_name}={new_key}\n")
    return new_key


_serializer = URLSafeTimedSerializer(_get_or_create_secret_key(), salt="cc-session")


def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_legacy_pbkdf2(password: str, stored_hash: str) -> bool:
    parts = stored_hash.split("$")
    if len(parts) != 3 or parts[0] != "pbkdf2_sha256":
        return False
    _, salt, hex_digest = parts
    try:
        expected = bytes.fromhex(hex_digest)
    except ValueError:
        return False
    computed = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), LEGACY_PBKDF2_ITERATIONS
    )
    return hmac.compare_digest(computed, expected)


def verify_password(password: str, stored_hash: str) -> tuple[bool, bool]:
    """Returns (is_valid, is_legacy_format)."""
    if stored_hash.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8")), False
        except ValueError:
            return False, False
    if stored_hash.startswith("pbkdf2_sha256$"):
        return _verify_legacy_pbkdf2(password, stored_hash), True
    return False, False


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserPublic(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: str


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _row_to_public(row: sqlite3.Row) -> UserPublic:
    return UserPublic(
        id=row["id"], first_name=row["first_name"], last_name=row["last_name"], email=row["email"]
    )


def _set_session_cookie(response: Response, user_id: int) -> None:
    token = _serializer.dumps({"user_id": user_id})
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,  # local dev over http — set True once served over HTTPS
        path="/",
    )


def get_current_user(request: Request) -> Optional[UserPublic]:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None

    con = get_connection()
    try:
        row = con.execute(
            "SELECT id, first_name, last_name, email FROM users WHERE id = ?",
            (data.get("user_id"),),
        ).fetchone()
    finally:
        con.close()

    return _row_to_public(row) if row is not None else None


@router.post("/register", response_model=UserPublic)
def register(payload: RegisterRequest, response: Response) -> UserPublic:
    first_name = payload.first_name.strip()
    last_name = payload.last_name.strip()
    email = payload.email.strip().lower()

    if not first_name or not last_name:
        raise HTTPException(400, "First and last name are required.")
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Enter a valid email address.")
    if len(payload.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if payload.password != payload.confirm_password:
        raise HTTPException(400, "Passwords do not match.")

    con = get_connection()
    try:
        existing = con.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email,)).fetchone()
        if existing is not None:
            raise HTTPException(409, "An account with this email already exists.")

        password_hash = hash_password(payload.password)
        name = f"{first_name} {last_name}"
        try:
            cur = con.execute(
                "INSERT INTO users (name, email, password_hash, first_name, last_name) "
                "VALUES (?, ?, ?, ?, ?)",
                (name, email, password_hash, first_name, last_name),
            )
            con.commit()
        except sqlite3.IntegrityError:
            raise HTTPException(409, "An account with this email already exists.")

        row = con.execute(
            "SELECT id, first_name, last_name, email FROM users WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    finally:
        con.close()

    _set_session_cookie(response, row["id"])
    return _row_to_public(row)


@router.post("/login", response_model=UserPublic)
def login(payload: LoginRequest, response: Response) -> UserPublic:
    email = payload.email.strip().lower()
    invalid_credentials = HTTPException(401, "Invalid email or password.")

    con = get_connection()
    try:
        row = con.execute(
            "SELECT id, first_name, last_name, email, password_hash FROM users WHERE LOWER(email) = ?",
            (email,),
        ).fetchone()
        if row is None:
            raise invalid_credentials

        is_valid, is_legacy = verify_password(payload.password, row["password_hash"])
        if not is_valid:
            raise invalid_credentials

        if is_legacy:
            con.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(payload.password), row["id"]),
            )
            con.commit()
    finally:
        con.close()

    _set_session_cookie(response, row["id"])
    return _row_to_public(row)


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"message": "Logged out."}


@router.get("/me", response_model=Optional[UserPublic])
def me(user: Optional[UserPublic] = Depends(get_current_user)) -> Optional[UserPublic]:
    return user
