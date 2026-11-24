
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.enums import PaymentStatus

logger = logging.getLogger(__name__)

class PaymentMonitoringService:

    @staticmethod
    async def get_stuck_payments(db: AsyncSession, minutes: int = 15) -> List[Payment]:
        threshold = datetime.now(timezone.utc) - timedelta(minutes=minutes)

        stmt = (
            select(Payment)
            .where(
                and_(
                    Payment.status == PaymentStatus.PENDING,
                    Payment.created_at < threshold
                )
            )
            .order_by(Payment.created_at)
        )

        result = await db.execute(stmt)
        payments = result.scalars().all()

        logger.info(f"Found {len(payments)} stuck payments (>{minutes} min)")
        return list(payments)

    @staticmethod
    async def get_failed_payments(
        db: AsyncSession,
        hours: int = 24,
        limit: int = 100
    ) -> List[Payment]:
        threshold = datetime.now(timezone.utc) - timedelta(hours=hours)

        stmt = (
            select(Payment)
            .where(
                and_(
                    Payment.status.in_([PaymentStatus.FAILED, PaymentStatus.CANCELLED]),
                    Payment.created_at >= threshold
                )
            )
            .order_by(Payment.created_at.desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        payments = result.scalars().all()

        logger.info(f"Found {len(payments)} failed payments in last {hours}h")
        return list(payments)

    @staticmethod
    async def get_payment_statistics(
        db: AsyncSession,
        hours: int = 24
    ) -> Dict[str, Any]:
        threshold = datetime.now(timezone.utc) - timedelta(hours=hours)

        status_stmt = (
            select(
                Payment.status,
                func.count(Payment.id).label('count'),
                func.sum(Payment.amount).label('total_amount')
            )
            .where(Payment.created_at >= threshold)
            .group_by(Payment.status)
        )

        result = await db.execute(status_stmt)
        status_stats = result.all()

        type_stmt = (
            select(
                Payment.payment_type,
                func.count(Payment.id).label('count'),
                func.sum(Payment.amount).label('total_amount')
            )
            .where(Payment.created_at >= threshold)
            .group_by(Payment.payment_type)
        )

        result = await db.execute(type_stmt)
        type_stats = result.all()

        stats = {
            "period_hours": hours,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "by_status": {
                str(row.status): {
                    "count": row.count,
                    "total_amount": float(row.total_amount or 0)
                }
                for row in status_stats
            },
            "by_type": {
                str(row.payment_type): {
                    "count": row.count,
                    "total_amount": float(row.total_amount or 0)
                }
                for row in type_stats
            }
        }

        total = sum(s["count"] for s in stats["by_status"].values())
        completed = stats["by_status"].get(PaymentStatus.COMPLETED.value, {}).get("count", 0)
        stats["success_rate"] = (completed / total * 100) if total > 0 else 0

        logger.info(f"Payment statistics for last {hours}h: success_rate={stats['success_rate']:.2f}%")

        return stats

    @staticmethod
    async def mark_expired_payments(db: AsyncSession) -> int:
        from app.services.payment_lifecycle import recover_payment, require_payments
        require_payments()
        threshold = datetime.now(timezone.utc) - timedelta(hours=1)
        ids = list((await db.scalars(
            select(Payment.id).where(
                Payment.status == PaymentStatus.PENDING, Payment.created_at < threshold
            ).limit(20)
        )).all())
        await db.commit()  # do not occupy a connection during independent recovery
        for payment_id in ids:
            await recover_payment(payment_id, force=True)
        return len(ids)

    @staticmethod
    async def check_expiring_subscriptions(
        db: AsyncSession,
        days: int = 7
    ) -> List[Subscription]:
        now = datetime.now(timezone.utc)
        threshold = now + timedelta(days=days)

        stmt = (
            select(Subscription)
            .where(
                and_(
                    Subscription.is_active == True,
                    Subscription.end_date <= threshold,
                    Subscription.end_date > now
                )
            )
            .order_by(Subscription.end_date)
        )

        result = await db.execute(stmt)
        subscriptions = result.scalars().all()

        logger.info(f"Found {len(subscriptions)} subscriptions expiring in {days} days")
        return list(subscriptions)

    @staticmethod
    async def get_user_payment_issues(
        db: AsyncSession,
        user_id: UUID
    ) -> Dict[str, Any]:
        failed_stmt = (
            select(Payment)
            .where(
                and_(
                    Payment.user_id == user_id,
                    Payment.status.in_([PaymentStatus.FAILED, PaymentStatus.CANCELLED])
                )
            )
            .order_by(Payment.created_at.desc())
            .limit(10)
        )

        result = await db.execute(failed_stmt)
        failed_payments = result.scalars().all()

        last_month = datetime.now(timezone.utc) - timedelta(days=30)
        recent_failed = [p for p in failed_payments if p.created_at >= last_month]

        issues = {
            "user_id": str(user_id),
            "total_failed_payments": len(failed_payments),
            "recent_failed_count": len(recent_failed),
            "last_failed_payment": failed_payments[0].created_at.isoformat() if failed_payments else None,
            "common_error_messages": {}
        }

        error_counts: Dict[str, int] = {}
        for payment in recent_failed:
            if payment.error_message:
                error_counts[payment.error_message] = error_counts.get(payment.error_message, 0) + 1

        issues["common_error_messages"] = dict(
            sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        )

        logger.info(f"Payment issues for user {user_id}: {issues['recent_failed_count']} recent failures")

        return issues
