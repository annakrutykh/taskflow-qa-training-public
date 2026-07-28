from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.security import cur
from app.schemas import (
    Login,
    Register,
    TokenResponse,
    UserResponse,
)
from app.services.auth import authenticate_user, logout_user, register_user

router = APIRouter(prefix="/auth", tags=["Auth"])

_register_rate_limit = rate_limit(
    action="register",
    env_prefix="RATE_LIMIT_REGISTER",
    default_max_attempts=10,
    default_window_seconds=60,
)
_login_rate_limit = rate_limit(
    action="login",
    env_prefix="RATE_LIMIT_LOGIN",
    default_max_attempts=5,
    default_window_seconds=60,
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Регистрация пользователя",
    description="Создает нового пользователя.",
    responses={
        201: {"description": "Пользователь успешно зарегистрирован"},
        409: {"description": "Email уже существует"},
        429: {"description": "Слишком много попыток регистрации с этого IP"},
    },
    dependencies=[Depends(_register_rate_limit)],
)
def register(
    body: Register,
    response: Response,
    db: Session = Depends(get_db),
):
    user = register_user(db, body.email, body.password, body.firstName, body.lastName)

    response.headers["Location"] = f"/api/v1/users/{user.id}"

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Авторизация",
    description="Возвращает JWT токен.",
    responses={
        200: {"description": "Авторизация успешна"},
        401: {"description": "Неверный логин или пароль"},
        429: {"description": "Слишком много попыток входа с этого IP"},
    },
    dependencies=[Depends(_login_rate_limit)],
)
def login(
    body: Login,
    db: Session = Depends(get_db),
):
    token = authenticate_user(db, body.email, body.password)

    return {
        "accessToken": token,
        "tokenType": "bearer",
    }


@router.post(
    "/logout",
    status_code=204,
    summary="Выход",
    description="Отзывает текущий accessToken — им нельзя будет "
    "воспользоваться повторно, даже до истечения срока действия.",
    responses={
        204: {"description": "Токен отозван"},
        401: {"description": "Не авторизован"},
    },
)
def logout(
    request: Request,
    user=Depends(cur),
):
    logout_user(request.state.jwt_jti, request.state.jwt_exp)

    return Response(status_code=204)
