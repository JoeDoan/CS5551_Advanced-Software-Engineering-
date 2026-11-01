from datetime import datetime, timedelta, timezone
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import case, delete, func
from sqlalchemy.exc import IntegrityError
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
    hash_password,
    require_coordinator,
    verify_password,
)
from app.models.entities import (
    AuthCredential,
    AuthSession,
    EditRequest,
    InstructorCourseAssignment,
    InstructorPreference,
    Schedule,
    User,
)
from app.schemas.api_schemas import (
    AccountAdminResponse,
    AccountCreateRequest,
    AccountUpdateRequest,
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


def _to_account_admin(cred: AuthCredential) -> AccountAdminResponse:
    return AccountAdminResponse(
        id=cred.id,
        email=cred.email,
        username=cred.username,
        full_name=cred.full_name,
        role=cred.role,
        department=cred.department,
        linked_user_id=cred.linked_user_id,
        is_active=cred.is_active,
    )


def _username_exists(session: Session, candidate: str, include_users: bool) -> bool:
    cred_hit = session.exec(
        select(AuthCredential.id).where(
            func.lower(AuthCredential.username) == candidate
        )
    ).first()
    if cred_hit is not None:
        return True
    if include_users:
        user_hit = session.exec(
            select(User.id).where(func.lower(User.username) == candidate)
        ).first()
        if user_hit is not None:
            return True
    return False


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
    if faculty is None:
        faculty = session.exec(
            select(AuthCredential)
            .where(AuthCredential.linked_user_id == 1)
            .order_by(AuthCredential.id)
        ).first()
    if faculty is None:
        faculty = session.exec(
            select(AuthCredential)
            .where(func.lower(AuthCredential.role) == "instructor")
            .order_by(AuthCredential.id)
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


@router.get("/accounts", response_model=List[AccountAdminResponse])
def list_accounts(
    role: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
    principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    """List managed authentication accounts ordered with coordinators first."""
    ensure_auth_accounts(session)

    stmt = select(AuthCredential)
    if role is not None and role.strip():
        stmt = stmt.where(func.lower(AuthCredential.role) == role.strip().lower())

    if search is not None and search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                AuthCredential.full_name.ilike(term),
                AuthCredential.email.ilike(term),
                AuthCredential.username.ilike(term),
                AuthCredential.department.ilike(term),
            )
        )

    role_rank = case(
        (func.lower(AuthCredential.role) == "coordinator", 0),
        else_=1,
    )
    stmt = stmt.order_by(
        role_rank, func.lower(AuthCredential.full_name), AuthCredential.id
    )
    return [_to_account_admin(cred) for cred in session.exec(stmt).all()]


@router.post(
    "/accounts",
    status_code=status.HTTP_201_CREATED,
    response_model=AccountAdminResponse,
)
def create_account(
    payload: AccountCreateRequest,
    session: Session = Depends(get_session),
    principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    """Create a coordinator or instructor account with linked User row for instructors."""
    ensure_auth_accounts(session)

    email = payload.email.strip().lower()
    department = payload.department.strip().upper()
    full_name = payload.full_name.strip()

    if "@" not in email or not email.split("@", 1)[0] or not email.split("@", 1)[1]:
        raise HTTPException(status_code=422, detail="Invalid email address.")
    if len(full_name) < 2:
        raise HTTPException(
            status_code=422, detail="Full name must be at least 2 characters."
        )
    if len(department) < 2:
        raise HTTPException(
            status_code=422, detail="Department must be at least 2 characters."
        )

    dup_email_cred = session.exec(
        select(AuthCredential.id).where(func.lower(AuthCredential.email) == email)
    ).first()
    dup_email_user = (
        session.exec(select(User.id).where(func.lower(User.email) == email)).first()
        if payload.role == "instructor"
        else None
    )
    if dup_email_cred is not None or dup_email_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account with email '{email}' already exists",
        )

    explicit_username = (
        payload.username.strip().lower()
        if payload.username and payload.username.strip()
        else None
    )
    if explicit_username is not None:
        if _username_exists(
            session,
            explicit_username,
            include_users=(payload.role == "instructor"),
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{explicit_username}' already exists",
            )
        username = explicit_username
    else:
        base_username = email.split("@")[0].lower()
        candidate = base_username
        suffix = 1
        while _username_exists(session, candidate, include_users=True):
            candidate = f"{base_username}{suffix}"
            suffix += 1
        username = candidate

    password_hash = hash_password(payload.password)
    linked_user_id: Optional[int] = None

    try:
        if payload.role == "instructor":
            new_user = User(
                username=username,
                email=email,
                full_name=full_name,
                role="instructor",
                department=department,
                priority_score=100000,
            )
            session.add(new_user)
            session.flush()
            linked_user_id = new_user.id

        cred = AuthCredential(
            email=email,
            username=username,
            full_name=full_name,
            role=payload.role,
            department=department,
            linked_user_id=linked_user_id,
            password_hash=password_hash,
            is_active=True,
        )
        session.add(cred)
        session.commit()
        session.refresh(cred)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account with matching email or username already exists",
        )

    return _to_account_admin(cred)


@router.patch("/accounts/{account_id}", response_model=AccountAdminResponse)
def update_account(
    account_id: int,
    payload: AccountUpdateRequest,
    session: Session = Depends(get_session),
    principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    """Update account attributes, sync linked User row, and revoke sessions on deactivation."""
    cred = session.get(AuthCredential, account_id)
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    if principal is not None and principal.id == account_id:
        if payload.is_active is False or (
            payload.role is not None and payload.role != "coordinator"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate or demote your own active coordinator account.",
            )

    if payload.full_name is not None:
        cleaned_name = payload.full_name.strip()
        if len(cleaned_name) < 2:
            raise HTTPException(
                status_code=422, detail="Full name must be at least 2 characters."
            )
        cred.full_name = cleaned_name

    if payload.department is not None:
        cleaned_dept = payload.department.strip().upper()
        if len(cleaned_dept) < 2:
            raise HTTPException(
                status_code=422, detail="Department must be at least 2 characters."
            )
        cred.department = cleaned_dept

    if payload.role is not None:
        cred.role = payload.role

    if payload.password is not None:
        cred.password_hash = hash_password(payload.password)

    if payload.is_active is not None:
        cred.is_active = payload.is_active

    if payload.role == "instructor" and cred.linked_user_id is None:
        existing_user = session.exec(
            select(User).where(func.lower(User.email) == cred.email.lower())
        ).first()
        if existing_user is not None:
            cred.linked_user_id = existing_user.id
        else:
            new_user = User(
                username=cred.username,
                email=cred.email,
                full_name=cred.full_name,
                role="instructor",
                department=cred.department,
                priority_score=100000,
            )
            session.add(new_user)
            session.flush()
            cred.linked_user_id = new_user.id

    if cred.linked_user_id is not None:
        linked_user = session.get(User, cred.linked_user_id)
        if linked_user is not None:
            linked_user.full_name = cred.full_name
            linked_user.department = cred.department
            if payload.role is not None:
                linked_user.role = cred.role
            session.add(linked_user)

    if payload.is_active is False:
        for auth_sess in session.exec(
            select(AuthSession).where(AuthSession.credential_id == account_id)
        ).all():
            if not auth_sess.revoked:
                auth_sess.revoked = True
                session.add(auth_sess)

    session.add(cred)
    session.commit()
    session.refresh(cred)
    return _to_account_admin(cred)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    session: Session = Depends(get_session),
    principal: Optional[SessionPrincipal] = Depends(require_coordinator),
):
    """Delete an account, its sessions, and any linked User and dependent records."""
    cred = session.get(AuthCredential, account_id)
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    if principal is not None and principal.id == account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own active coordinator account.",
        )

    session.execute(
        delete(AuthSession).where(AuthSession.credential_id == account_id)
    )

    linked_uid = cred.linked_user_id
    session.delete(cred)
    session.flush()

    if linked_uid is not None:
        sched_ids = list(
            session.exec(
                select(Schedule.id).where(Schedule.user_id == linked_uid)
            ).all()
        )
        if sched_ids:
            session.execute(
                delete(EditRequest).where(
                    or_(
                        EditRequest.requester_id == linked_uid,
                        EditRequest.schedule_id.in_(sched_ids),
                    )
                )
            )
        else:
            session.execute(
                delete(EditRequest).where(EditRequest.requester_id == linked_uid)
            )
        session.execute(delete(Schedule).where(Schedule.user_id == linked_uid))
        session.execute(
            delete(InstructorCourseAssignment).where(
                InstructorCourseAssignment.user_id == linked_uid
            )
        )
        session.execute(
            delete(InstructorPreference).where(
                InstructorPreference.user_id == linked_uid
            )
        )
        session.execute(delete(User).where(User.id == linked_uid))

    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
