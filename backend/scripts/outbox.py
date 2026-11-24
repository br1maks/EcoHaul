"""Inspect/recover deliveries without printing payloads or credentials."""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, or_, select
from app.core.database import async_session_maker, engine
from app.models.outbox import OutboxMessage


async def main(args) -> None:
    async with async_session_maker() as db:
        pending = (OutboxMessage.delivered_at.is_(None), OutboxMessage.discarded_at.is_(None))
        if args.command == "status":
            summary = (
                await db.execute(
                    select(
                        OutboxMessage.channel,
                        func.count(),
                        func.min(OutboxMessage.created_at),
                        func.max(OutboxMessage.attempts),
                    )
                    .where(*pending)
                    .group_by(OutboxMessage.channel)
                )
            ).all()
            print(
                json.dumps(
                    [
                        {
                            "channel": channel,
                            "pending": count,
                            "oldest": str(oldest),
                            "max_attempts": attempts,
                        }
                        for channel, count, oldest, attempts in summary
                    ]
                )
            )
            messages = (
                await db.scalars(
                    select(OutboxMessage).where(*pending).order_by(OutboxMessage.sequence).limit(20)
                )
            ).all()
            for message in messages:
                print(
                    json.dumps(
                        {
                            "event_id": str(message.event_id),
                            "channel": message.channel,
                            "attempts": message.attempts,
                            "error": message.last_error,
                            "available_at": message.available_at.isoformat(),
                        }
                    )
                )
        elif args.command in {"retry", "discard"}:
            message = await db.scalar(
                select(OutboxMessage)
                .where(
                    OutboxMessage.event_id == args.event_id,
                    *pending,
                )
                .with_for_update(of=OutboxMessage)
            )
            if message is None:
                raise SystemExit(
                    "Pending event not found; terminal events are never replayed by this tool"
                )
            if args.command == "retry":
                message.available_at = datetime.now(timezone.utc)
            else:
                message.discarded_at = datetime.now(timezone.utc)
                message.discard_reason = args.reason
            await db.commit()
            print(json.dumps({"event_id": str(message.event_id), "action": args.command}))
        elif args.command == "purge":
            cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
            result = await db.execute(
                delete(OutboxMessage).where(
                    or_(OutboxMessage.delivered_at < cutoff, OutboxMessage.discarded_at < cutoff)
                )
            )
            await db.commit()
            print(json.dumps({"deleted_terminal_events": result.rowcount}))


async def run(args) -> None:
    try:
        await main(args)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    retry = commands.add_parser("retry")
    retry.add_argument("event_id", type=UUID)
    discard = commands.add_parser(
        "discard", help="Intentionally abandon an undeliverable event; unblocks its stream"
    )
    discard.add_argument("event_id", type=UUID)
    discard.add_argument(
        "--reason", required=True, help="Short operational reason; do not include private payloads"
    )
    purge = commands.add_parser("purge")
    purge.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    if args.command == "purge" and args.days < 1:
        parser.error("--days must be at least 1; pending events are never purged")
    if args.command == "discard" and not 1 <= len(args.reason) <= 200:
        parser.error("--reason must contain 1 to 200 characters")
    asyncio.run(run(args))
