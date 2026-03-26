
from typing import Optional
from app.services.payment_provider import PaymentProvider, PaymentProviderType
from app.services.yookassa_provider import YooKassaProvider
from app.core.config import settings

class PaymentFactory:

    _providers = {
        PaymentProviderType.YOOKASSA: YooKassaProvider,
    }

    @classmethod
    def get_provider(cls, provider_type: Optional[PaymentProviderType] = None) -> PaymentProvider:
        if provider_type is None:
            provider_type = getattr(
                settings,
                'PAYMENT_PROVIDER',
                PaymentProviderType.YOOKASSA
            )

        provider_class = cls._providers.get(provider_type)

        if provider_class is None:
            raise ValueError(
                f"Payment provider '{provider_type}' is not supported. "
                f"Supported providers: {list(cls._providers.keys())}"
            )

        return provider_class()

    @classmethod
    def register_provider(
        cls,
        provider_type: PaymentProviderType,
        provider_class: type[PaymentProvider]
    ):
        cls._providers[provider_type] = provider_class

def get_payment_provider() -> PaymentProvider:
    return PaymentFactory.get_provider()
