"""Exercise the real REST adapter without opening a network connection."""
import json
from decimal import Decimal

import httpx
import pytest
from app.services.yookassa_service import ProviderRejected, YooKassaService


@pytest.mark.parametrize("status", [200, 400, 500])
def test_provider_request_preserves_money_key_and_ambiguous_errors(monkeypatch, status):
    original_client = httpx.Client
    seen = []

    def transport(request):
        seen.append(request)
        return httpx.Response(
            status,
            json={
                "id": "payment-1",
                "status": "pending",
                "amount": {"value": "5.10", "currency": "BYN"},
                "confirmation": {"confirmation_url": "https://example.test/pay"},
            },
        )

    def client(**options):
        assert options["timeout"].connect == 5 and options["timeout"].read == 10
        return original_client(transport=httpx.MockTransport(transport), **options)

    monkeypatch.setattr(httpx, "Client", client)

    def create():
        return YooKassaService.create_payment(
            amount=Decimal("5.10"),
            description="Test",
            return_url="https://example.test/return",
            idempotence_key="stable-key",
            currency="BYN",
            metadata={"payment_id": "local-id"},
        )

    if status == 200:
        result = create()
        assert result.amount.value == Decimal("5.10")
    else:
        with pytest.raises(ProviderRejected if status == 400 else httpx.HTTPStatusError):
            create()
    assert len(seen) == 1
    assert str(seen[0].url) == "https://api.yookassa.ru/v3/payments"
    assert seen[0].headers["Idempotence-Key"] == "stable-key"
    assert json.loads(seen[0].content)["amount"] == {"value": "5.10", "currency": "BYN"}
