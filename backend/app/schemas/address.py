

from typing import Optional, Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.models.enums import AddressLabel
from app.schemas.common import BaseSchema, UUIDMixin, TimestampMixin, SoftDeleteMixin
from app.core.config import settings

class AddressBase(BaseSchema):
    latitude: float = Field(..., ge=-90, le=90, description="Широта")
    longitude: float = Field(..., ge=-180, le=180, description="Долгота")
    full_address: str = Field(..., min_length=10, max_length=500)
    city: str = Field("Минск", min_length=1, max_length=100)
    district: str = Field(..., min_length=1, max_length=100)
    street: str = Field(..., min_length=1, max_length=200)
    house_number: str = Field(..., min_length=1, max_length=20)
    apartment: Optional[str] = Field(None, max_length=20)
    entrance: Optional[int] = Field(None, ge=1, le=50)
    floor: Optional[int] = Field(None, ge=-1, le=100)
    label: Optional[AddressLabel] = None
    is_default: bool = False
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("street")
    @classmethod
    def validate_street(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Улица не может быть пустой")

        street_lower = v.lower()
        allowed_streets = settings.current_phase_streets

        if street_lower not in allowed_streets:
            raise ValueError(
                f"Улица '{v}' не входит в зону обслуживания. "
                f"Доступные улицы: {', '.join(allowed_streets)}"
            )

        return v

    @field_validator("house_number")
    @classmethod
    def validate_house_number(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Номер дома не может быть пустым")
        return v

class AddressCreate(AddressBase):
    yandex_geocoder_response: Optional[str] = None

    @model_validator(mode="after")
    def validate_default_address_logic(self):
        return self

class AddressUpdate(BaseSchema):
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Широта")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Долгота")
    full_address: Optional[str] = Field(None, min_length=10, max_length=500)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    district: Optional[str] = Field(None, min_length=1, max_length=100)
    street: Optional[str] = Field(None, min_length=1, max_length=200)
    house_number: Optional[str] = Field(None, min_length=1, max_length=20)
    apartment: Optional[str] = Field(None, max_length=20)
    entrance: Optional[int] = Field(None, ge=1, le=50)
    floor: Optional[int] = Field(None, ge=-1, le=100)
    label: Optional[AddressLabel] = None
    is_default: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("street")
    @classmethod
    def validate_street(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None

        v = v.strip()
        if not v:
            raise ValueError("Улица не может быть пустой")

        street_lower = v.lower()
        allowed_streets = settings.current_phase_streets

        if street_lower not in allowed_streets:
            raise ValueError(
                f"Улица '{v}' не входит в зону обслуживания. "
                f"Доступные улицы: {', '.join(allowed_streets)}"
            )

        return v

    @field_validator("house_number")
    @classmethod
    def validate_house_number(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Номер дома не может быть пустым")
        return v

class AddressResponse(UUIDMixin, TimestampMixin, SoftDeleteMixin, AddressBase):
    user_id: UUID
    yandex_geocoder_response: Optional[str] = None

    short_address: str
    full_address_with_details: str
    coordinates_tuple: tuple[float, float]

    @model_validator(mode="before")
    @classmethod
    def calculate_computed_fields(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            model_data = {
                "id": data.id,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "deleted_at": data.deleted_at,
                "user_id": data.user_id,
                "latitude": data.latitude,
                "longitude": data.longitude,
                "full_address": data.full_address,
                "city": data.city,
                "district": data.district,
                "street": data.street,
                "house_number": data.house_number,
                "apartment": data.apartment,
                "entrance": data.entrance,
                "floor": data.floor,
                "label": data.label,
                "is_default": data.is_default,
                "notes": data.notes,
                "yandex_geocoder_response": data.yandex_geocoder_response,
                "short_address": getattr(data, "short_address", ""),
                "full_address_with_details": getattr(data, "full_address_with_details", ""),
                "coordinates_tuple": getattr(data, "coordinates_tuple", (0.0, 0.0)),
            }
            data = model_data
        elif isinstance(data, dict):
            if "short_address" not in data:
                parts = [data.get("street", ""), data.get("house_number", "")]
                if data.get("apartment"):
                    parts.append(f"кв. {data['apartment']}")
                data["short_address"] = ", ".join(filter(None, parts))

            if "full_address_with_details" not in data:
                parts = [data.get("full_address", "")]
                if data.get("entrance"):
                    parts.append(f"подъезд {data['entrance']}")
                if data.get("floor"):
                    parts.append(f"этаж {data['floor']}")
                if data.get("apartment"):
                    parts.append(f"кв. {data['apartment']}")
                data["full_address_with_details"] = ", ".join(filter(None, parts))

            if "coordinates_tuple" not in data:
                data["coordinates_tuple"] = (data.get("latitude", 0.0), data.get("longitude", 0.0))

        return data

class AddressBrief(UUIDMixin, BaseSchema):
    latitude: float
    longitude: float
    short_address: str
    district: str
    label: Optional[AddressLabel] = None
    is_default: bool
