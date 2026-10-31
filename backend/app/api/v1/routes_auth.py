from datetime import datetime, timedelta, timezone
import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, or_, select

from app.core.config import settings
from app.core.database import get_session
from app.core.security import (
    COORDINATOR_DEFAULT_EMAIL,
    COORDINATOR_DEFAULT_PASSWORD,
    FACULTY_DEFAULT_PASSWORD,
    SessionPrincipal,
    create_access_token,
    ensure_auth_accounts,
    get_active_session_principal,
    verify_password,
)
from app.models.entities import AuthCredential, AuthSession
from app.schemas.api_schemas import (
    AuthUserResponse,
    DemoAccountResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    SessionMeResponse,
)

router = APIRouter()

DEMO_FACULTY_EMAIL = "leeyu@umkc.edu"


def _to_auth_user(cred: AuthCredential) -> AuthUserResponse:
    return AuthUserResponse(
        id=cred.id,
        email=cred.email,
        username=cred.username,
        full_name=cred.full_name,
        role=cred.role,
        department=cred.department,
        linked_user_id=cred.linked_user_id,
    )


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    session: Session = Depends(get_session),
):
    """Authenticate by email or username, issue JWT, and persist active session."""
    ensure_auth_accounts(session)

    lookup = (payload.identifier or payload.email or payload.username or "").strip()
    if not lookup or not payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password",
        )

    lookup_lower = lookup.lower()
    cred = session.exec(
        select(AuthCredential).where(
            or_(
                func.lower(AuthCredential.email) == lookup_lower,
                func.lower(AuthCredential.username) == lookup_lower,
            )
        )
    ).first()

    if (
        cred is None
        or not cred.is_active
        or not verify_password(payload.password, cred.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password",
        )

    now = datetime.now(timezone.utc)
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = (now + expires_delta).isoformat()
    jti = secrets.token_urlsafe(24)

    access_token = create_access_token(
        data={
            "sub": str(cred.id),
            "email": cred.email,
            "username": cred.username,
            "role": cred.role,
            "jti": jti,
        },
        expires_delta=expires_delta,
    )

    auth_sess = AuthSession(
        token_jti=jti,
        credential_id=cred.id,
        expires_at=expires_at,
        revoked=False,
        created_at=now.isoformat(),
    )
    session.add(auth_sess)
    session.commit()

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        session_id=jti,
        expires_at=expires_at,
        user=_to_auth_user(cred),
    )


@router.get("/me", response_model=SessionMeResponse)
def get_current_session(
    principal: SessionPrincipal = Depends(get_active_session_principal),
):
    """Verify current bearer session and return authenticated user metadata."""
    return SessionMeResponse(
        session_id=principal.session_id,
        expires_at=principal.expires_at,
        user=_to_auth_user(principal.credential),
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    principal: SessionPrincipal = Depends(get_active_session_principal),
    session: Session = Depends(get_session),
):
    """Revoke the current server-side session token immediately."""
    auth_sess = principal.auth_session
    auth_sess.revoked = True
    session.add(auth_sess)
    session.commit()
    return LogoutResponse(
        status="logged_out",
        revoked_session_id=auth_sess.token_jti,
    )


@router.get("/demo-accounts", response_model=List[DemoAccountResponse])
def list_demo_accounts(
    session: Session = Depends(get_session),
):
    """Return quick demo login metadata for Coordinator and Faculty portals."""
    ensure_auth_accounts(session)

    coord = session.exec(
        select(AuthCredential).where(
            func.lower(AuthCredential.email) == COORDINATOR_DEFAULT_EMAIL
        )
    ).first()
    faculty = session.exec(
        select(AuthCredential).where(
            func.lower(AuthCredential.email) == DEMO_FACULTY_EMAIL
        )
    ).first()

    accounts: List[DemoAccountResponse] = []
    if coord is not None:
        accounts.append(
            DemoAccountResponse(
                email=coord.email,
                username=coord.username,
                full_name=coord.full_name,
                role=coord.role,
                department=coord.department,
                password=COORDINATOR_DEFAULT_PASSWORD,
                linked_user_id=coord.linked_user_id,
            )
        )

    if faculty is not None:
        accounts.append(
            DemoAccountResponse(
                email=faculty.email,
                username=faculty.username,
                full_name=faculty.full_name,
                role=faculty.role,
                department=faculty.department,
                password=FACULTY_DEFAULT_PASSWORD,
                linked_user_id=faculty.linked_user_id,
            )
        )
    else:
        accounts.append(
            DemoAccountResponse(
                email=DEMO_FACULTY_EMAIL,
                username="leeyu",
                full_name="Dr. Yugyung Lee",
                role="instructor",
                department="CS",
                password=FACULTY_DEFAULT_PASSWORD,
                linked_user_id=1,
            )
        )

    return accounts
