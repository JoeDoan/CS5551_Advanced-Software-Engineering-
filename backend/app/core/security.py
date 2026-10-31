import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import secrets
from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.models.entities import AuthCredential, AuthSession, User

PBKDF2_ITERATIONS = 100_000
COORDINATOR_DEFAULT_EMAIL = "coordinator@umkc.edu"
COORDINATOR_DEFAULT_USERNAME = "coordinator"
COORDINATOR_DEFAULT_PASSWORD = "coordinator123"
FACULTY_DEFAULT_PASSWORD = "faculty123"


@dataclass(frozen=True)
class SessionPrincipal:
    credential: AuthCredential
    auth_session: AuthSession

    @property
    def id(self) -> Optional[int]:
        return self.credential.id

    @property
    def email(self) -> str:
        return self.credential.email

    @property
    def username(self) -> str:
        return self.credential.username

    @property
    def full_name(self) -> str:
        return self.credential.full_name

    @property
    def role(self) -> str:
        return self.credential.role

    @property
    def department(self) -> str:
        return self.credential.department

    @property
    def linked_user_id(self) -> Optional[int]:
        return self.credential.linked_user_id

    @property
    def session_id(self) -> str:
        return self.auth_session.token_jti

    @property
    def expires_at(self) -> str:
        return self.auth_session.expires_at


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def hash_password(password: str, salt: Optional[str] = None) -> str:
    chosen_salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        chosen_salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${chosen_salt}${derived.hex()}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        algorithm, iter_str, salt, expected_hex = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
    except (ValueError, AttributeError):
        return False

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return hmac.compare_digest(derived.hex(), expected_hex)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    now = datetime.now(timezone.utc)
    delta = (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    expire = now + delta

    payload = dict(data)
    payload.setdefault("jti", secrets.token_urlsafe(24))
    payload["iat"] = int(now.timestamp())
    payload["exp"] = int(expire.timestamp())

    header_b64 = _b64url_encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode(
            "utf-8"
        )
    )
    payload_b64 = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed authentication token.")

    header_b64, payload_b64, sig_b64 = parts
    try:
        header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
    except Exception as exc:
        raise ValueError("Invalid token header.") from exc

    if not isinstance(header, dict) or header.get("alg") != "HS256":
        raise ValueError("Unsupported token signing algorithm.")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = _b64url_encode(
        hmac.new(
            settings.JWT_SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
    )
    if not hmac.compare_digest(expected_sig, sig_b64):
        raise ValueError("Invalid token signature.")

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception as exc:
        raise ValueError("Invalid token payload.") from exc

    if not isinstance(payload, dict) or "exp" not in payload:
        raise ValueError("Token missing expiration claim.")

    try:
        exp_ts = float(payload["exp"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid token expiration claim.") from exc

    if datetime.now(timezone.utc).timestamp() >= exp_ts:
        raise ValueError("Authentication token has expired.")

    return payload


def ensure_auth_accounts(session: Session) -> None:
    """Idempotently bootstrap coordinator and faculty credentials from users."""
    existing_creds = session.exec(select(AuthCredential)).all()
    by_email = {cred.email.lower(): cred for cred in existing_creds}
    used_usernames = {cred.username.lower() for cred in existing_creds}
    changed = False

    if COORDINATOR_DEFAULT_EMAIL not in by_email:
        coord_uname = COORDINATOR_DEFAULT_USERNAME
        if coord_uname in used_usernames:
            coord_uname = "course_coordinator"
        coord_cred = AuthCredential(
            email=COORDINATOR_DEFAULT_EMAIL,
            username=coord_uname,
            full_name="Course Coordinator",
            role="coordinator",
            department="CS",
            linked_user_id=None,
            password_hash=hash_password(COORDINATOR_DEFAULT_PASSWORD),
            is_active=True,
        )
        session.add(coord_cred)
        by_email[COORDINATOR_DEFAULT_EMAIL] = coord_cred
        used_usernames.add(coord_uname)
        changed = True

    for user in session.exec(select(User)).all():
        email_key = user.email.lower()
        existing = by_email.get(email_key)
        if existing is not None:
            if existing.linked_user_id != user.id:
                existing.linked_user_id = user.id
                session.add(existing)
                changed = True
            continue

        candidate_uname = user.username
        if candidate_uname.lower() in used_usernames:
            candidate_uname = f"{user.username}_{user.id}"
        used_usernames.add(candidate_uname.lower())

        inst_cred = AuthCredential(
            email=user.email,
            username=candidate_uname,
            full_name=user.full_name,
            role="instructor",
            department=user.department,
            linked_user_id=user.id,
            password_hash=hash_password(FACULTY_DEFAULT_PASSWORD),
            is_active=True,
        )
        session.add(inst_cred)
        by_email[email_key] = inst_cred
        changed = True

    if changed:
        session.commit()


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_active_session_principal(
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
) -> SessionPrincipal:
    if not authorization or not authorization.strip():
        raise _unauthorized("Authentication required. Please log in.")

    parts = authorization.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise _unauthorized("Invalid authorization header. Expected Bearer token.")

    token = parts[1].strip()
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise _unauthorized(str(exc)) from exc

    jti = payload.get("jti")
    if not isinstance(jti, str) or not jti:
        raise _unauthorized("Authentication token missing session identifier.")

    auth_sess = session.exec(
        select(AuthSession).where(AuthSession.token_jti == jti)
    ).first()
    if auth_sess is None or auth_sess.revoked:
        raise _unauthorized("Session is invalid or has been revoked.")

    try:
        expires_dt = datetime.fromisoformat(auth_sess.expires_at)
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= expires_dt:
            raise _unauthorized("Session has expired. Please log in again.")
    except ValueError as exc:
        raise _unauthorized("Invalid session expiration record.") from exc

    cred = session.get(AuthCredential, auth_sess.credential_id)
    if cred is None or not cred.is_active:
        raise _unauthorized("Account is inactive or no longer exists.")

    return SessionPrincipal(credential=cred, auth_session=auth_sess)


get_Active_session_principal = get_active_session_principal


def require_auth(
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
) -> Optional[SessionPrincipal]:
    if authorization is not None and authorization.strip() != "":
        return get_active_session_principal(
            authorization=authorization, session=session
        )
    if settings.require_auth:
        raise _unauthorized("Authentication required. Please log in.")
    return None


def require_coordinator(
    principal: Optional[SessionPrincipal] = Depends(require_auth),
) -> Optional[SessionPrincipal]:
    if principal is not None and principal.role not in ("coordinator", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coordinator permissions required for this action.",
        )
    return principal
