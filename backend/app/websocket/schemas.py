from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

class WSMessageType(str, Enum):

    CONNECTED = "CONNECTED"
    NEW_NOTIFICATION = "NEW_NOTIFICATION"
    NEW_ORDER = "NEW_ORDER"
    ORDER_ASSIGNED = "ORDER_ASSIGNED"
    ORDER_STATUS_CHANGED = "ORDER_STATUS_CHANGED"
    PING = "PING"

    PONG = "PONG"
    MARK_READ = "MARK_READ"

class WSMessage(BaseModel):
    type: WSMessageType = Field(..., description="Тип сообщения")
    data: dict[str, Any] = Field(default_factory=dict, description="Данные сообщения")

def create_notification_message(notification: dict) -> dict:
    return {
        "type": WSMessageType.NEW_NOTIFICATION.value,
        "data": {
            "id": str(notification["id"]),
            "title": notification["title"],
            "message": notification["message"],
            "priority": notification["priority"],
            "created_at": (
                notification["created_at"].isoformat()
                if isinstance(notification["created_at"], datetime)
                else notification["created_at"]
            ),
        }
    }

def create_order_status_message(
    order_id: UUID,
    status: str,
    message: str,
    old_status: str | None = None
) -> dict:
    data = {
        "order_id": str(order_id),
        "new_status": status,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if old_status:
        data["old_status"] = old_status

    return {
        "type": WSMessageType.ORDER_STATUS_CHANGED.value,
        "data": data
    }

def create_new_order_message(order: dict) -> dict:
    return {
        "type": WSMessageType.NEW_ORDER.value,
        "data": {
            "order_id": str(order["id"]),
            "pickup_address": order.get("pickup_address"),
            "delivery_address": order.get("delivery_address"),
            "garbage_type": order.get("garbage_type"),
            "number_of_bags": order.get("number_of_bags"),
            "final_price": float(order.get("final_price", 0)),
            "created_at": (
                order["created_at"].isoformat()
                if isinstance(order["created_at"], datetime)
                else order["created_at"]
            ),
        }
    }

def create_order_assigned_message(
    order_id: UUID,
    courier_name: str,
    courier_phone: str,
    courier_rating: float,
    message: str
) -> dict:
    return {
        "type": WSMessageType.ORDER_ASSIGNED.value,
        "data": {
            "order_id": str(order_id),
            "courier_name": courier_name,
            "courier_phone": courier_phone,
            "courier_rating": round(courier_rating, 1),
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
