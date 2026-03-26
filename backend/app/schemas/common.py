
from datetime import datetime
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

class UUIDMixin(BaseModel):
    id: UUID = Field(
        ...,
        description="Уникальный идентификатор записи (UUID v4)",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )

class TimestampMixin(BaseModel):
    created_at: datetime = Field(
        ...,
        description="Дата и время создания записи (UTC с timezone)",
        examples=["2025-11-08T10:30:00+00:00"],
    )
    updated_at: datetime = Field(
        ...,
        description="Дата и время последнего обновления (UTC с timezone)",
        examples=["2025-11-08T12:45:00+00:00"],
    )

class SoftDeleteMixin(BaseModel):
    deleted_at: Optional[datetime] = Field(
        None,
        description="Дата и время мягкого удаления (NULL = активна)",
        examples=[None, "2025-11-08T15:00:00+00:00"],
    )

class PaginationParams(BaseModel):
    

    page: int = Field(
        1,
        ge=1,
        description="Номер страницы (начинается с 1)",
        examples=[1, 2, 3],
    )
    size: int = Field(
        20,
        ge=1,
        le=100,
        description="Количество элементов на странице (максимум 100)",
        examples=[10, 20, 50],
    )

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.size

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):

    items: List[T] = Field(
        ...,
        description="Список элементов текущей страницы",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Общее количество элементов (во всей коллекции)",
        examples=[0, 150, 1000],
    )
    page: int = Field(
        ...,
        ge=1,
        description="Номер текущей страницы",
        examples=[1, 2, 3],
    )
    size: int = Field(
        ...,
        ge=1,
        description="Количество элементов на странице",
        examples=[10, 20, 50],
    )

    @property
    def pages(self) -> int:
        if self.total == 0:
            return 0
        return (self.total + self.size - 1) // self.size  

class MessageResponse(BaseModel):

    message: str = Field(
        ...,
        description="Текст сообщения",
        examples=["Операция выполнена успешно", "Пользователь создан"],
    )

class ErrorDetail(BaseModel):

    loc: List[str] = Field(..., description="Путь к полю с ошибкой")
    msg: str = Field(..., description="Сообщение об ошибке")
    type: str = Field(..., description="Тип ошибки")

class ErrorResponse(BaseModel):

    detail: List[ErrorDetail] | str = Field(
        ...,
        description="Список деталей ошибок или строка с описанием",
        examples=[
            "Пользователь не найден",
            [{"loc": ["body", "email"], "msg": "Invalid", "type": "value_error"}],
        ],
    )

class BaseSchema(BaseModel):
  
    model_config = ConfigDict(
        from_attributes=True, 
        populate_by_name=True,  
        str_strip_whitespace=True,  
        use_enum_values=True, 
    )

