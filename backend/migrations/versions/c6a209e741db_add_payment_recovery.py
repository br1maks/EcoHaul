"""Persist immutable checkout intent, provider idempotency and recovery state."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c6a209e741db"
down_revision = "b47a2f019e60"
branch_labels = None
depends_on = None


def upgrade():
    for column in [
        sa.Column("currency", sa.String(3), nullable=False, server_default="BYN"),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True)),
        sa.Column("request_hash", sa.String(64)),
        sa.Column("checkout_payload", postgresql.JSONB()),
        sa.Column("creation_state", sa.String(20), nullable=False, server_default="LEGACY"),
        sa.Column("provider_key", postgresql.UUID(as_uuid=True)),
        sa.Column("provider_key_deadline", sa.DateTime(timezone=True)),
        sa.Column("creation_lease", postgresql.UUID(as_uuid=True)),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("confirmation_url", sa.Text()),
        sa.Column("checkout_expires_at", sa.DateTime(timezone=True)),
        sa.Column("next_reconcile_at", sa.DateTime(timezone=True)),
        sa.Column("reconcile_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("settlement_applied_at", sa.DateTime(timezone=True)),
    ]:
        op.add_column("payments", column)
    op.create_unique_constraint(
        "uq_payment_user_idempotency", "payments", ["user_id", "idempotency_key"]
    )
    op.create_unique_constraint("uq_payment_provider_key", "payments", ["provider_key"])
    op.create_index("ix_payment_reconcile", "payments", ["status", "next_reconcile_at"])
    op.execute(
        "UPDATE payments SET settlement_applied_at=COALESCE(completed_at,created_at) WHERE status='COMPLETED'"
    )


def downgrade():
    op.drop_index("ix_payment_reconcile", "payments")
    op.drop_constraint("uq_payment_provider_key", "payments", type_="unique")
    op.drop_constraint("uq_payment_user_idempotency", "payments", type_="unique")
    for name in (
        "settlement_applied_at",
        "reconcile_attempts",
        "next_reconcile_at",
        "checkout_expires_at",
        "confirmation_url",
        "lease_until",
        "creation_lease",
        "provider_key_deadline",
        "provider_key",
        "creation_state",
        "checkout_payload",
        "request_hash",
        "idempotency_key",
        "currency",
    ):
        op.drop_column("payments", name)
