"""Persist delivery intents in the domain transaction.

Revision ID: b47a2f019e60
Revises: 3bde9578fc08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b47a2f019e60"
down_revision = "3bde9578fc08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_messages",
        sa.Column("sequence", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("stream", sa.String(200), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discard_reason", sa.String(200), nullable=True),
        sa.Column("last_error", sa.String(100), nullable=True),
        sa.CheckConstraint(
            "channel IN ('websocket', 'telegram', 'cache')", name="ck_outbox_channel"
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_outbox_attempts"),
        sa.CheckConstraint(
            "delivered_at IS NULL OR discarded_at IS NULL", name="ck_outbox_terminal_state"
        ),
    )
    op.create_index(
        "ix_outbox_ready",
        "outbox_messages",
        ["channel", "available_at", "sequence"],
        postgresql_where=sa.text("delivered_at IS NULL AND discarded_at IS NULL"),
    )
    op.create_index(
        "ix_outbox_stream",
        "outbox_messages",
        ["channel", "stream", "sequence"],
        postgresql_where=sa.text("delivered_at IS NULL AND discarded_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("outbox_messages")
