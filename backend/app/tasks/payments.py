import asyncio

from app.celery_app import celery_app
from app.services.payment_lifecycle import reconcile_batch


@celery_app.task
def reconcile_payments():
    return asyncio.run(reconcile_batch())
