
from typing import Optional, Any, List, Tuple
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.common import BaseSchema, UUIDMixin, TimestampMixin, SoftDeleteMixin

GeoJSONCoordinates = List[List[List[float]]]

WKTString = str

def validate_geojson_polygon(geojson: dict) -> dict:

    if not isinstance(geojson, dict):
        raise ValueError("GeoJSON должен быть словарём (dict)")

    if "type" not in geojson:
        raise ValueError("GeoJSON должен содержать ключ 'type'")

    if "coordinates" not in geojson:
        raise ValueError("GeoJSON должен содержать ключ 'coordinates'")

    if geojson["type"] != "Polygon":
        raise ValueError(f"Тип должен быть 'Polygon', получен '{geojson['type']}'")

  
    coordinates = geojson["coordinates"]
    if not isinstance(coordinates, list) or len(coordinates) == 0:
        raise ValueError("coordinates должны быть непустым массивом колец")

    for ring_idx, ring in enumerate(coordinates):
        ring_name = "внешнее кольцо" if ring_idx == 0 else f"внутреннее кольцо #{ring_idx}"

        if not isinstance(ring, list):
            raise ValueError(f"{ring_name}: должно быть массивом точек")

        if len(ring) < 4:
            raise ValueError(
                f"{ring_name}: должно содержать минимум 4 точки "
                f"(3 вершины + замыкающая). Получено: {len(ring)}"
            )

        for point_idx, point in enumerate(ring):
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError(
                    f"{ring_name}, точка #{point_idx}: "
                    f"должна быть [longitude, latitude]. Получено: {point}"
                )

            lng, lat = point

            if not isinstance(lng, (int, float)) or not isinstance(lat, (int, float)):
                raise ValueError(
                    f"{ring_name}, точка #{point_idx}: "
                    f"координаты должны быть числами. Получено: lng={lng}, lat={lat}"
                )

            if not (-180 <= lng <= 180):
                raise ValueError(
                    f"{ring_name}, точка #{point_idx}: "
                    f"longitude должна быть в пределах -180..180. Получено: {lng}"
                )

            if not (-90 <= lat <= 90):
                raise ValueError(
                    f"{ring_name}, точка #{point_idx}: "
                    f"latitude должна быть в пределах -90..90. Получено: {lat}"
                )

        
        first_point = ring[0]
        last_point = ring[-1]

        if first_point != last_point:
            raise ValueError(
                f"{ring_name}: полигон должен быть замкнут "
                f"(первая и последняя точка должны совпадать). "
                f"Первая: {first_point}, Последняя: {last_point}"
            )

    return geojson

def geojson_to_wkt(geojson: dict) -> str:

    coordinates = geojson["coordinates"]

    rings = []
    for ring in coordinates:
        
        points = [f"{point[0]} {point[1]}" for point in ring]
        ring_str = f"({', '.join(points)})"
        rings.append(ring_str)

    return f"POLYGON({', '.join(rings)})"

def wkt_to_geojson(wkt: str) -> dict:

    wkt = wkt.strip()
    if not wkt.startswith("POLYGON"):
        raise ValueError(f"WKT должен начинаться с 'POLYGON'. Получено: {wkt}")

    
    wkt = wkt[7:].strip()

    
    rings = []
    depth = 0
    current_ring = ""

    for char in wkt:
        if char == "(":
            depth += 1
            if depth == 2: 
                current_ring = ""
            elif depth > 2:
                current_ring += char
        elif char == ")":
            depth -= 1
            if depth == 1: 
                rings.append(current_ring)
                current_ring = ""
            elif depth > 1:
                current_ring += char
        elif depth >= 2:
            current_ring += char

    coordinates = []
    for ring_str in rings:
        points = []
        for point_str in ring_str.split(","):
            point_str = point_str.strip()
            if point_str:
                parts = point_str.split()
                if len(parts) == 2:
                    lng = float(parts[0])
                    lat = float(parts[1])
                    points.append([lng, lat])
        if points:
            coordinates.append(points)

    return {
        "type": "Polygon",
        "coordinates": coordinates,
    }

class ServiceZoneBase(BaseSchema):
 

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Название зоны обслуживания",
        examples=["ЖК Минск Мир", "Центральный район", "Советский район"],
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Описание зоны",
        examples=[
            "Экспериментальный многофункциональный комплекс на месте бывшего аэропорта Минск-1",
            "Центральный район Минска",
            None,
        ],
    )
    polygon: dict = Field(
        ...,
        description="Полигон зоны в формате GeoJSON",
        examples=[
            {
                "type": "Polygon",
                "coordinates": [[
                    [27.530, 53.855],
                    [27.560, 53.855],
                    [27.560, 53.877],
                    [27.530, 53.877],
                    [27.530, 53.855],
                ]],
            }
        ],
    )
    is_active: bool = Field(
        True,
        description="Активна ли зона (если False - заказы не принимаются)",
        examples=[True, False],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Название зоны не может быть пустым")
        return v

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, v: Any) -> dict:
        if isinstance(v, str):
            try:
                v = wkt_to_geojson(v)
            except Exception as e:
                raise ValueError(f"Некорректный WKT формат: {e}")

        try:
            return validate_geojson_polygon(v)
        except ValueError as e:
            raise ValueError(f"Некорректный полигон: {e}")

class ServiceZoneCreate(ServiceZoneBase):

    pass

class ServiceZoneUpdate(BaseSchema):

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Новое название зоны",
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Новое описание зоны",
    )
    polygon: Optional[dict] = Field(
        None,
        description="Новый полигон зоны в формате GeoJSON",
    )
    is_active: Optional[bool] = Field(
        None,
        description="Новый статус активности зоны",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("Название зоны не может быть пустым")
        return v

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, v: Optional[Any]) -> Optional[dict]:
        if v is None:
            return None

        if isinstance(v, str):
            try:
                v = wkt_to_geojson(v)
            except Exception as e:
                raise ValueError(f"Некорректный WKT формат: {e}")

        try:
            return validate_geojson_polygon(v)
        except ValueError as e:
            raise ValueError(f"Некорректный полигон: {e}")

class ServiceZoneResponse(UUIDMixin, TimestampMixin, SoftDeleteMixin, ServiceZoneBase):

    is_available: bool = Field(
        ...,
        description="Доступна ли зона для заказов (is_active AND NOT deleted)",
    )
    polygon_wkt: str = Field(
        ...,
        description="WKT представление полигона",
        examples=["POLYGON((27.530 53.855, 27.560 53.855, 27.560 53.877, 27.530 53.877, 27.530 53.855))"],
    )
    bounds: List[float] = Field(
        ...,
        description="Bounding box: [min_lng, min_lat, max_lng, max_lat]",
        examples=[[27.530, 53.855, 27.560, 53.877]],
    )
    center: List[float] = Field(
        ...,
        description="Центр полигона (приблизительно): [lng, lat]",
        examples=[[27.545, 53.866]],
    )

    @model_validator(mode="before")
    @classmethod
    def calculate_computed_fields(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            is_available = getattr(data, "is_available", None)

            data = {
                "id": data.id,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
                "deleted_at": data.deleted_at,
                "name": data.name,
                "description": data.description,
                "polygon": data.polygon if isinstance(data.polygon, dict) else {},
                "is_active": data.is_active,
                "is_available": is_available if is_available is not None else (data.is_active and data.deleted_at is None),
            }

        elif isinstance(data, dict):
            if "is_available" not in data:
                data["is_available"] = data.get("is_active", True) and data.get("deleted_at") is None

        if "polygon_wkt" not in data and "polygon" in data:
            try:
                data["polygon_wkt"] = geojson_to_wkt(data["polygon"])
            except Exception:
                data["polygon_wkt"] = ""

        if "bounds" not in data or "center" not in data:
            try:
                polygon = data.get("polygon", {})
                if polygon and "coordinates" in polygon and polygon["coordinates"]:
                    outer_ring = polygon["coordinates"][0]

                    lngs = [point[0] for point in outer_ring]
                    lats = [point[1] for point in outer_ring]

                    min_lng = min(lngs)
                    max_lng = max(lngs)
                    min_lat = min(lats)
                    max_lat = max(lats)

                    if "bounds" not in data:
                        data["bounds"] = [min_lng, min_lat, max_lng, max_lat]

                    if "center" not in data:
                        center_lng = (min_lng + max_lng) / 2
                        center_lat = (min_lat + max_lat) / 2
                        data["center"] = [center_lng, center_lat]
                else:
                    if "bounds" not in data:
                        data["bounds"] = [0.0, 0.0, 0.0, 0.0]
                    if "center" not in data:
                        data["center"] = [0.0, 0.0]
            except Exception:
                if "bounds" not in data:
                    data["bounds"] = [0.0, 0.0, 0.0, 0.0]
                if "center" not in data:
                    data["center"] = [0.0, 0.0]

        return data

class ServiceZoneBrief(UUIDMixin, BaseSchema):

    name: str = Field(..., description="Название зоны")
    is_active: bool = Field(..., description="Активна ли зона")
    is_available: bool = Field(..., description="Доступна ли зона")

"""
ЧТО МЫ СОЗДАЛИ:

1. ServiceZoneBase - базовые поля зоны с GeoJSON полигоном
   └─ Валидация полигона: GeoJSON + WKT поддержка
   └─ Проверка замкнутости контура
   └─ Проверка диапазонов координат

2. ServiceZoneCreate - для создания зоны
   └─ Используется админом для добавления зон
   └─ Валидация уникальности name в БД

3. ServiceZoneUpdate - для обновления зоны
   └─ Все поля опциональные
   └─ Частичное обновление (PATCH)

4. ServiceZoneResponse - полный ответ с computed fields
   └─ Все поля из модели
   └─ Computed fields: is_available, polygon_wkt, bounds, center
   └─ Для отображения на картах и PostGIS запросов

5. ServiceZoneBrief - краткая версия для списков
   └─ Только id, name, is_active, is_available
   └─ Без polygon (экономия трафика)

ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ:
- validate_geojson_polygon() - валидация GeoJSON Polygon
- geojson_to_wkt() - конвертация GeoJSON → WKT
- wkt_to_geojson() - конвертация WKT → GeoJSON

ПАТТЕРНЫ:
- Base: общие поля + валидация полигона
- Create: Base (без дополнительных полей)
- Update: частичная версия Base (все Optional)
- Response: Base + все поля модели + computed fields
- Brief: минимальный набор для списков

ЭТАПЫ ИСПОЛЬЗОВАНИЯ:
- ЭТАП 1 (MVP): Одна зона "ЖК Минск Мир"
  Полигон: прямоугольник 53.855-53.877°N, 27.530-27.560°E

- ЭТАП 2 (Production): Несколько зон по районам Минска
  Полигоны: сложные формы реальных районов

ФОРМАТЫ ГЕОМЕТРИИ:
1. GeoJSON (для веб-карт): {"type": "Polygon", "coordinates": [...]}
2. WKT (для PostGIS): "POLYGON((lng lat, lng lat, ...))"

ИСПОЛЬЗОВАНИЕ:
```python
# Создание зоны (админ)
zone = ServiceZoneCreate(
    name="ЖК Минск Мир",
    description="Экспериментальный комплекс",
    polygon={
        "type": "Polygon",
        "coordinates": [[
            [27.530, 53.855], [27.560, 53.855],
            [27.560, 53.877], [27.530, 53.877],
            [27.530, 53.855]
        ]]
    },
    is_active=True
)

# Получение зоны
zone: ServiceZoneResponse = await service.get_zone(zone_id)
print(f"Зона: {zone.name}")
print(f"Доступна: {zone.is_available}")
print(f"Центр: {zone.center}")
print(f"WKT: {zone.polygon_wkt}")

# Список зон (краткий)
zones: List[ServiceZoneBrief] = await service.get_zones_brief()
```

ДОСТУП:
- CLIENT: Только is_available=True зоны (для выбора адреса)
- COURIER: Только is_available=True зоны (для фильтрации заказов)
- ADMIN: Все зоны (CRUD операции)
"""
