
from typing import Optional, Dict, Any
from yookassa import Configuration, Payment as YKPayment
from app.core.config import settings

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

class YooKassaService:

    @staticmethod
    def create_payment(
        amount: float,
        description: str,
        return_url: str,
        save_payment_method: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        payment_data = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "BYN"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,
            "save_payment_method": save_payment_method,
            "description": description
        }

        if metadata:
            payment_data["metadata"] = metadata

        payment = YKPayment.create(payment_data)
        return payment

    @staticmethod
    def create_payment_with_saved_method(
        amount: float,
        payment_method_id: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        payment_data = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "BYN"
            },
            "payment_method_id": payment_method_id,
            "capture": True,
            "description": description
        }

        if metadata:
            payment_data["metadata"] = metadata

        payment = YKPayment.create(payment_data)
        return payment

    @staticmethod
    def get_payment_info(payment_id: str) -> Dict[str, Any]:
        payment = YKPayment.find_one(payment_id)
        return payment

    @staticmethod
    def cancel_payment(payment_id: str) -> Dict[str, Any]:
        payment = YKPayment.cancel(payment_id)
        return payment

    @staticmethod
    def verify_webhook_ip(client_ip: str) -> bool:
        from ipaddress import ip_address, ip_network

        allowed_networks = [
            "185.71.76.0/27",
            "185.71.77.0/27",
            "77.75.153.0/25",
            "77.75.154.128/25",
            "2a02:5180::/32",
        ]

        allowed_ips = [
            "77.75.156.11",
            "77.75.156.35",
        ]

        try:
            client = ip_address(client_ip)

            if client_ip in allowed_ips:
                return True

            for network in allowed_networks:
                if client in ip_network(network):
                    return True

            return False

        except ValueError:
            return False
