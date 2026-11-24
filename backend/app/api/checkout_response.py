from app.models.payment import Payment
from app.schemas.checkout import CheckoutResponse
from fastapi import Response


def checkout_response(payment: Payment, response: Response) -> CheckoutResponse:
    if payment.status == "PENDING" and not payment.confirmation_url:
        response.status_code = 202
        response.headers["Retry-After"] = "2"
    return CheckoutResponse(
        payment_id=payment.id,
        payment_url=payment.confirmation_url,
        amount=float(payment.amount),
        status=payment.status,
        creation_state=payment.creation_state,
        expires_at=payment.checkout_expires_at,
    )
