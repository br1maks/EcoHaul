from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.sessions import validate_access
from app.models.enums import UserRole
from app.models.user import User

bearer_scheme = HTTPBearer()

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:

    user, session = await validate_access(db, credentials.credentials)
    request.state.auth_session_id = session.id
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
