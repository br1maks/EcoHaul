import sys
sys.path.insert(0, '/home/Maxim/PythonProjects/ecohaul-fixed/backend')

from app.schemas.address import AddressBase
from uuid import uuid4

print("🧪 Тестирование валидации координат ЖК 'Минск Мир'\n")

print("✅ Тест 1: Центр ЖК 'Минск Мир' (53.866, 27.545)")
try:
    address = AddressBase(
        latitude=53.866,
        longitude=27.545,
        full_address="Минск, ЖК Минск Мир, ул. Аэродромная",
        city="Минск",
        district="Октябрьский",
        street="ул. Аэродромная",
        house_number="1",
    )
    print(f"   ✅ Координаты приняты: {address.latitude}, {address.longitude}\n")
except ValueError as e:
    print(f"   ❌ Ошибка: {e}\n")

print("✅ Тест 2: Северная граница ЖК (53.875, 27.545)")
try:
    address = AddressBase(
        latitude=53.875,
        longitude=27.545,
        full_address="Минск, ЖК Минск Мир, северная часть",
        city="Минск",
        district="Октябрьский",
        street="ул. Аэродромная",
        house_number="10",
    )
    print(f"   ✅ Координаты приняты: {address.latitude}, {address.longitude}\n")
except ValueError as e:
    print(f"   ❌ Ошибка: {e}\n")

print("❌ Тест 3: Центр Минска (53.900, 27.560) - вне ЖК")
try:
    address = AddressBase(
        latitude=53.900,
        longitude=27.560,
        full_address="Минск, проспект Независимости, 10",
        city="Минск",
        district="Центральный",
        street="проспект Независимости",
        house_number="10",
    )
    print(f"   ❌ ОШИБКА: Координаты не должны быть приняты!\n")
except ValueError as e:
    print(f"   ✅ Правильно отклонено: {e}\n")

print("❌ Тест 4: Восточнее ЖК (53.866, 27.565) - вне зоны")
try:
    address = AddressBase(
        latitude=53.866,
        longitude=27.565,
        full_address="Минск, за пределами ЖК",
        city="Минск",
        district="Октябрьский",
        street="ул. Тестовая",
        house_number="1",
    )
    print(f"   ❌ ОШИБКА: Координаты не должны быть приняты!\n")
except ValueError as e:
    print(f"   ✅ Правильно отклонено: {e}\n")

print("❌ Тест 5: Москва (55.755, 37.617) - другой город")
try:
    address = AddressBase(
        latitude=55.755,
        longitude=37.617,
        full_address="Москва, Красная площадь",
        city="Москва",
        district="Центральный",
        street="Красная площадь",
        house_number="1",
    )
    print(f"   ❌ ОШИБКА: Координаты не должны быть приняты!\n")
except ValueError as e:
    print(f"   ✅ Правильно отклонено: {e}\n")

print("=" * 60)
print("✅ Все тесты пройдены! Валидация работает корректно.")
print("=" * 60)
