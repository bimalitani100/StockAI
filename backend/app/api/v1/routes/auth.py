from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.config import settings
from app.core.security import create_access_token
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    UserResponse,
)
from app.services.auth import (
    CurrentPasswordIncorrectError,
    PasswordUnchangedError,
    authenticate_user,
    change_password,
    get_user_by_email,
    register_user,
    update_profile,
)

router = APIRouter()


def set_session_cookie(response: Response, user_id) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=create_access_token(user_id),
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    response: Response,
    database: DatabaseSession,
) -> AuthResponse:
    if get_user_by_email(database, request.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")
    try:
        user = register_user(database, request)
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        ) from error
    set_session_cookie(response, user.id)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(
    request: LoginRequest,
    response: Response,
    database: DatabaseSession,
) -> AuthResponse:
    user = authenticate_user(database, request.email, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    set_session_cookie(response, user.id)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


@router.get("/me", response_model=AuthResponse)
def me(current_user: CurrentUser) -> AuthResponse:
    return AuthResponse(user=UserResponse.model_validate(current_user))


@router.patch("/me", response_model=AuthResponse)
def update_me(
    request: ProfileUpdateRequest,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> AuthResponse:
    user = update_profile(database, current_user, request)
    return AuthResponse(user=UserResponse.model_validate(user))


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def update_password(
    request: PasswordChangeRequest,
    current_user: CurrentUser,
    database: DatabaseSession,
) -> None:
    try:
        change_password(database, current_user, request)
    except (CurrentPasswordIncorrectError, PasswordUnchangedError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
