from fastapi import APIRouter

from app.api.v1 import (
    auth,
    users,
    addresses,
    orders,
    service_zones,
    subscriptions,
    payments,
    admin_payments,
    admin_statistics,
    admin,
    scheduled_tasks,
    verification,
    courier_shifts,
    reviews,
    notifications,
    courier_applications,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(addresses.router)
api_router.include_router(orders.router)
api_router.include_router(service_zones.router)
api_router.include_router(subscriptions.router)
api_router.include_router(payments.router)
api_router.include_router(admin_payments.router)
api_router.include_router(admin_statistics.router)
api_router.include_router(admin.router)
api_router.include_router(scheduled_tasks.router)
api_router.include_router(verification.router)
api_router.include_router(courier_shifts.router)
api_router.include_router(reviews.router)
api_router.include_router(notifications.router)
api_router.include_router(courier_applications.router)
