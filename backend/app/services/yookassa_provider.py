
from typing import Dict, Any, Optional
from app.services.payment_provider import PaymentProvider
from app.services.yookassa_service import YooKassaService

class YooKassaProvider(PaymentProvider):

    def __init__(self):
        self.service = YooKassaService()

    def create_payment(
        self,
        amount: float,
        description: str,
        return_url: str,
        save_payment_method: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        payment = self.service.create_payment(
            amount=amount,
            description=description,
            return_url=return_url,
            save_payment_method=save_payment_method,
            metadata=metadata
        )

        return {
            "payment_id": payment.id,
            "confirmation_url": payment.confirmation.confirmation_url if payment.confirmation else None,
            "status": payment.status,
            "amount": float(payment.amount.value),
            "currency": payment.amount.currency,
            "created_at": payment.created_at,
            "metadata": payment.metadata,
            "raw_response": payment
        }

    def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        payment = self.service.get_payment_info(payment_id)

        return {
            "payment_id": payment.id,
            "status": payment.status,
            "amount": float(payment.amount.value),
            "currency": payment.amount.currency,
            "paid": payment.paid,
            "created_at": payment.created_at,
            "captured_at": getattr(payment, 'captured_at', None),
            "metadata": payment.metadata,
            "raw_response": payment
        }

    def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        payment = self.service.cancel_payment(payment_id)

        return {
            "payment_id": payment.id,
            "status": payment.status,
            "cancelled": payment.status == "canceled",
            "raw_response": payment
        }

    def verify_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
        # The provider's authenticated API is the source of truth, not a custom HMAC.
        remote = self.service.get_payment_info(payload["object"]["id"])
        return remote.status == payload["object"].get("status")

    def create_refund(
        self,
        payment_id: str,
        amount: Optional[float] = None
    ) -> Dict[str, Any]:
        raise NotImplementedError("Refund functionality not yet implemented for YooKassa")
