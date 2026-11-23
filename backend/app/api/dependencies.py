from fastapi import Depends, HTTPException, status
from uuid import UUID
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    if payload.get("type") != "access":
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    try:
        user_id = UUID(user_id)
    except (ValueError, TypeError, AttributeError):
        raise credentials_exception

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь заблокирован",
        )
    return current_user

async def require_client(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль клиента",
        )
    return current_user

async def require_courier(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role != UserRole.COURIER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль курьера",
        )
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Курьер не верифицирован",
        )
    return current_user

async def require_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль админа",
        )
    return current_user


async def require_order_operator(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role == UserRole.ADMIN:
        return current_user
    if current_user.role == UserRole.COURIER and current_user.is_verified:
        return current_user
    raise HTTPException(status_code=403, detail="Требуется верифицированный курьер или администратор")
