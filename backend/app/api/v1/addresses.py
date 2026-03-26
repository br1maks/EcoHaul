from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.address import Address
from app.schemas.address import AddressCreate, AddressUpdate, AddressResponse

router = APIRouter(prefix="/addresses", tags=["Адреса"])

@router.get("", response_model=list[AddressResponse])
async def get_my_address(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Address).where(
        Address.user_id == current_user.id,
        Address.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    addresses = result.scalars().all()
    return addresses

@router.post("", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
async def create_address(
    data: AddressCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    address = Address(
        user_id=current_user.id,
        latitude=data.latitude,
        longitude=data.longitude,
        location=f"POINT({data.longitude} {data.latitude})",
        full_address=data.full_address,
        city=data.city,
        district=data.district,
        street=data.street,
        house_number=data.house_number,
        apartment=data.apartment,
        entrance=data.entrance,
        floor=data.floor,
        label=data.label,
        is_default=data.is_default,
        notes=data.notes,
    )
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return address

@router.get("/{address_id}", response_model=AddressResponse)
async def get_address(
    address_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Address).where(
        Address.id == address_id,
        Address.user_id == current_user.id,
        Address.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    address = result.scalar_one_or_none()

    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Адрес не найден",
        )
    return address

@router.patch("/{address_id}", response_model=AddressResponse)
async def update_address(
    data: AddressUpdate,
    address_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Address).where(
        Address.id == address_id,
        Address.user_id == current_user.id,
        Address.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    address = result.scalar_one_or_none()

    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Адрес не найден",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(address, field, value)

    await db.commit()
    await db.refresh(address)
    return address

@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Address).where(
        Address.id == address_id,
        Address.user_id == current_user.id,
        Address.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    address = result.scalar_one_or_none()

    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Адрес не найден",
        )

    address.deleted_at = datetime.now(timezone.utc)
    await db.commit()
