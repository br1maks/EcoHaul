from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.dependencies import require_admin
from app.models.user import User
from app.models.order import Order
from app.models.subscription import Subscription
from app.models.notification import Notification
from app.models.courier_shift import CourierShift
from app.models.enums import (
    OrderStatus,
    NotificationType,
    NotificationChannel,
)
from app.websocket.connection_manager import manager
from app.websocket.schemas import create_notification_message

router = APIRouter(prefix="/scheduled-tasks", tags=["Автозадачи"])

class TaskResult(BaseModel):
    task_name: str
    success: bool
    processed_count: int
    message: str
    execution_time_ms: float

class ScheduledTasksResult(BaseModel):
    tasks: list[TaskResult]
    total_success: int
    total_failed: int
    total_execution_time_ms: float

@router.post("/renew-subscriptions", response_model=TaskResult)
async def renew_subscriptions_task(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    start_time = datetime.now()

    try:
        now = datetime.now(timezone.utc)

        stmt = select(Subscription).where(
            and_(
                Subscription.is_active.is_(True),
                Subscription.end_date <= now,
                Subscription.auto_renew_enabled.is_(True)
            )
        )

        result = await db.execute(stmt)
        expired_subscriptions = result.scalars().all()

        renewed_count = 0

        for subscription in expired_subscriptions:
            user_stmt = select(User).where(User.id == subscription.user_id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if not user:
                continue

            subscription.start_date = subscription.end_date
            subscription.end_date = subscription.end_date + timedelta(days=30)
            subscription.renewed_count += 1

            subscription.next_billing_date = subscription.end_date

            notification = Notification(
                user_id=user.id,
                subscription_id=subscription.id,
                notification_type=NotificationType.SUBSCRIPTION_RENEWED,
                channel=NotificationChannel.IN_APP,
                title="Подписка продлена",
                message=f"Ваша подписка \"{subscription.tier.value}\" успешно продлена до {subscription.end_date.strftime('%d.%m.%Y')}",
                sent_at=now,
            )
            db.add(notification)

            await db.flush()

            ws_message = create_notification_message({
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "priority": "medium",
                "created_at": notification.sent_at,
            })
            await manager.send_personal_message(user.id, ws_message)

            renewed_count += 1

        await db.commit()

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return TaskResult(
            task_name="renew_subscriptions",
            success=True,
            processed_count=renewed_count,
            message=f"Продлено {renewed_count} подписок",
            execution_time_ms=round(execution_time, 2),
        )

    except Exception as e:
        await db.rollback()
        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return TaskResult(
            task_name="renew_subscriptions",
            success=False,
            processed_count=0,
            message=f"Ошибка: {str(e)}",
            execution_time_ms=round(execution_time, 2),
        )

@router.post("/cleanup-old-orders", response_model=TaskResult)
async def cleanup_old_orders_task(
    hours: int = 24,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    start_time = datetime.now()

    try:
        threshold = datetime.now(timezone.utc) - timedelta(hours=hours)

        stmt = select(Order).where(
            and_(
                Order.status == OrderStatus.PENDING,
                Order.created_at <= threshold
            )
        )

        result = await db.execute(stmt)
        old_orders = result.scalars().all()

        cancelled_count = 0

        for order in old_orders:
            order.status = OrderStatus.CANCELLED

            notification = Notification(
                user_id=order.client_id,
                order_id=order.id,
                notification_type=NotificationType.ORDER_CANCELLED,
                channel=NotificationChannel.IN_APP,
                title="Заказ отменён",
                message=f"Заказ #{order.id} был автоматически отменён из-за отсутствия курьера в течение {hours} часов",
                sent_at=datetime.now(timezone.utc),
            )
            db.add(notification)

            await db.flush()

            from app.websocket.schemas import create_order_status_message
            ws_message = create_order_status_message(
                order_id=order.id,
                status="CANCELLED",
                message=f"Заказ автоматически отменён (не найден курьер)",
                old_status="PENDING"
            )
            await manager.send_personal_message(order.client_id, ws_message)

            cancelled_count += 1

        await db.commit()

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return TaskResult(
            task_name="cleanup_old_orders",
            success=True,
            processed_count=cancelled_count,
            message=f"Отменено {cancelled_count} старых заказов (старше {hours} часов)",
            execution_time_ms=round(execution_time, 2),
        )

    except Exception as e:
        await db.rollback()
        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return TaskResult(
            task_name="cleanup_old_orders",
            success=False,
            processed_count=0,
            message=f"Ошибка: {str(e)}",
            execution_time_ms=round(execution_time, 2),
        )

@router.post("/notify-expiring-subscriptions", response_model=TaskResult)
async def notify_expiring_subscriptions_task(
    days_before: int = 3,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    start_time = datetime.now()

    try:
        now = datetime.now(timezone.utc)
        threshold_start = now + timedelta(days=days_before)
        threshold_end = threshold_start + timedelta(days=1)

        stmt = select(Subscription).where(
            and_(
                Subscription.is_active.is_(True),
                Subscription.end_date >= threshold_start,
                Subscription.end_date < threshold_end
            )
        )

        result = await db.execute(stmt)
        expiring_subscriptions = result.scalars().all()

        notified_count = 0

        for subscription in expiring_subscriptions:
            notification = Notification(
                user_id=subscription.user_id,
                subscription_id=subscription.id,
                notification_type=NotificationType.SUBSCRIPTION_EXPIRING,
                channel=NotificationChannel.IN_APP,
                title="Подписка заканчивается",
                message=f"Ваша подписка \"{subscription.tier.value}\" заканчивается {subscription.end_date.strftime('%d.%m.%Y')}. "
                        f"{'Подписка будет автоматически продлена.' if subscription.auto_renew_enabled else 'Продлите подписку, чтобы продолжить пользоваться сервисом.'}",
                sent_at=now,
            )
            db.add(notification)

            await db.flush()
            
            ws_message = create_notification_message({
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "priority": "high",
                "created_at": notification.sent_at,
            })
            await manager.send_personal_message(subscription.user_id, ws_message)

            notified_count += 1

        await db.commit()

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return TaskResult(
            task_name="notify_expiring_subscriptions",
            success=True,
            processed_count=notified_count,
            message=f"Отправлено {notified_count} уведомлений об истекающих подписках",
            execution_time_ms=round(execution_time, 2),
        )

    except Exception as e:
        await db.rollback()
        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return TaskResult(
            task_name="notify_expiring_subscriptions",
            success=False,
            processed_count=0,
            message=f"Ошибка: {str(e)}",
            execution_time_ms=round(execution_time, 2),
        )

@router.post("/send-daily-courier-stats", response_model=TaskResult)
async def send_daily_courier_stats_task(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    start_time = datetime.now()

    try:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        stmt = select(CourierShift).where(
            and_(
                CourierShift.started_at >= today_start,
                CourierShift.started_at < today_end,
                CourierShift.ended_at.isnot(None)
            )
        )

        result = await db.execute(stmt)
        today_shifts = result.scalars().all()

        courier_stats = {}
        for shift in today_shifts:
            if shift.courier_id not in courier_stats:
                courier_stats[shift.courier_id] = {
                    'shifts': 0,
                    'orders': 0,
                    'distance': 0.0,
                    'hours': 0.0,
                }

            courier_stats[shift.courier_id]['shifts'] += 1
            courier_stats[shift.courier_id]['orders'] += shift.orders_completed
            courier_stats[shift.courier_id]['distance'] += float(shift.total_distance_km or 0)

            if shift.ended_at and shift.started_at:
                duration = (shift.ended_at - shift.started_at).total_seconds() / 3600
                courier_stats[shift.courier_id]['hours'] += duration

        notified_count = 0

        for courier_id, stats in courier_stats.items():
            message = (
                f"Статистика за сегодня:\n\n"
                f"Смен: {stats['shifts']}\n"
                f"Заказов: {stats['orders']}\n"
                f"Часов работы: {stats['hours']:.1f}\n"
                f"Пройдено: {stats['distance']:.1f} км\n\n"
                f"Отличная работа!"
            )

            notification = Notification(
                user_id=courier_id,
                notification_type=NotificationType.DAILY_STATS,
                channel=NotificationChannel.IN_APP,
                title="Статистика за день",
                message=message,
                sent_at=datetime.now(timezone.utc),
            )
            db.add(notification)

            ws_message = {
                "type": "DAILY_STATS",
                "data": {
                    "shifts": stats['shifts'],
                    "orders": stats['orders'],
                    "hours": round(stats['hours'], 1),
                    "distance_km": round(stats['distance'], 1),
                    "message": message,
                    "date": today_start.strftime("%Y-%m-%d"),
                }
            }
            await manager.send_personal_message(courier_id, ws_message)

            notified_count += 1

        await db.commit()

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return TaskResult(
            task_name="send_daily_courier_stats",
            success=True,
            processed_count=notified_count,
            message=f"Отправлено {notified_count} уведомлений с ежедневной статистикой",
            execution_time_ms=round(execution_time, 2),
        )

    except Exception as e:
        await db.rollback()
        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return TaskResult(
            task_name="send_daily_courier_stats",
            success=False,
            processed_count=0,
            message=f"Ошибка: {str(e)}",
            execution_time_ms=round(execution_time, 2),
        )

@router.post("/run-all", response_model=ScheduledTasksResult)
async def run_all_tasks(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    start_time = datetime.now()

    tasks_results = []

    result1 = await renew_subscriptions_task(current_user=current_user, db=db)
    tasks_results.append(result1)

    result2 = await cleanup_old_orders_task(hours=24, current_user=current_user, db=db)
    tasks_results.append(result2)

    result3 = await notify_expiring_subscriptions_task(days_before=3, current_user=current_user, db=db)
    tasks_results.append(result3)

    result4 = await send_daily_courier_stats_task(current_user=current_user, db=db)
    tasks_results.append(result4)

    total_success = sum(1 for r in tasks_results if r.success)
    total_failed = sum(1 for r in tasks_results if not r.success)

    execution_time = (datetime.now() - start_time).total_seconds() * 1000

    return ScheduledTasksResult(
        tasks=tasks_results,
        total_success=total_success,
        total_failed=total_failed,
        total_execution_time_ms=round(execution_time, 2),
    )
