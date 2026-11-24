"""Bounded REST adapter. Public methods run outside the async event loop."""
from decimal import Decimal
from typing import Any, Literal
from urllib.parse import quote

import httpx
from app.core.config import settings
from pydantic import BaseModel, Field


class ProviderRejected(Exception):
    """Explicit creation rejection; provider response bodies are not persisted."""


class ProviderAmount(BaseModel):
    value: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class ProviderConfirmation(BaseModel):
    confirmation_url: str | None = None


class ProviderMethod(BaseModel):
    id: str | None = None
    saved: bool = False


class ProviderPayment(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    status: Literal["pending", "waiting_for_capture", "succeeded", "canceled"]
    amount: ProviderAmount
    metadata: dict[str, Any] | None = None
    confirmation: ProviderConfirmation | None = None
    payment_method: ProviderMethod | None = None


class YooKassaService:
    @staticmethod
    def _request(method: str, path: str, *, payload=None, idempotence_key=None):
        headers = {"Idempotence-Key": str(idempotence_key)} if idempotence_key else {}
        with httpx.Client(
            timeout=httpx.Timeout(10, connect=5),
            auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
        ) as client:
            response = client.request(
                method, "https://api.yookassa.ru/v3/" + path, headers=headers, json=payload
            )
        if method == "POST" and response.status_code in (400, 401, 403, 404, 422):
            raise ProviderRejected("Provider rejected the request")
        response.raise_for_status()
        data = response.json()
        return ProviderPayment.model_validate(data)

    @staticmethod
    def create_payment(
        *,
        amount: Decimal,
        description: str,
        return_url: str,
        save_payment_method=False,
        metadata=None,
        idempotence_key,
        currency=None,
    ):
        return YooKassaService._request(
            "POST",
            "payments",
            idempotence_key=idempotence_key,
            payload={
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": currency or settings.PAYMENT_CURRENCY,
                },
                "confirmation": {"type": "redirect", "return_url": return_url},
                "capture": True,
                "save_payment_method": save_payment_method,
                "description": description,
                "metadata": metadata or {},
            },
        )

    @staticmethod
    def get_payment_info(payment_id: str):
        return YooKassaService._request("GET", "payments/" + quote(payment_id, safe=""))
