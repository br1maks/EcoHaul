
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

class PaymentProviderType(str, Enum):
    YOOKASSA = "yookassa"
    STRIPE = "stripe"
    PAYPAL = "paypal"

class PaymentProvider(ABC):

    @abstractmethod
    def create_payment(
        self,
        amount: float,
        description: str,
        return_url: str,
        save_payment_method: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def verify_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
        pass

    @abstractmethod
    def create_refund(
        self,
        payment_id: str,
        amount: Optional[float] = None
    ) -> Dict[str, Any]:
        pass
