from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.models.service_zone import ServiceZone

class ServiceZoneResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}

class AddressCheckRequest(BaseModel):
    street: str = Field(..., min_length=1, max_length=200, description="Название улицы")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Широта (опционально)")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Долгота (опционально)")

class AddressCheckResponse(BaseModel):
    is_serviceable: bool = Field(..., description="Обслуживается ли адрес")
    message: str = Field(..., description="Сообщение пользователю")
    allowed_streets: Optional[list[str]] = Field(None, description="Список разрешённых улиц (если адрес не обслуживается)")
    current_phase: int = Field(..., description="Текущая фаза обслуживания")

router = APIRouter(prefix="/service-zones", tags=["Сервисные зоны"])

@router.get("", response_model=list[ServiceZoneResponse])
async def get_service_zones(
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ServiceZone).where(ServiceZone.is_active == True)
    result = await db.execute(stmt)
    zones = result.scalars().all()

    return zones

@router.get("/{zone_id}", response_model=ServiceZoneResponse)
async def get_service_zone(
    zone_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ServiceZone).where(ServiceZone.id == zone_id)
    result = await db.execute(stmt)
    zone = result.scalar_one_or_none()

    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Зона не найдена",
        )

    return zone

@router.post("/check-address", response_model=AddressCheckResponse)
async def check_address_serviceability(
    data: AddressCheckRequest,
):
   
    street_lower = data.street.strip().lower()
    allowed_streets = settings.current_phase_streets

  
    if street_lower in allowed_streets:
        return AddressCheckResponse(
            is_serviceable=True,
            message=f"Отлично! Улица '{data.street}' входит в зону обслуживания.",
            allowed_streets=None,
            current_phase=settings.CURRENT_PHASE,
        )

    return AddressCheckResponse(
        is_serviceable=False,
        message=f"К сожалению, улица '{data.street}' пока не входит в зону обслуживания.",
        allowed_streets=allowed_streets,
        current_phase=settings.CURRENT_PHASE,
    )
