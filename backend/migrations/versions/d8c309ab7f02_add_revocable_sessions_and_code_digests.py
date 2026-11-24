"""Revocable refresh families, persistent attempt budgets and protected code storage."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d8c309ab7f02"
down_revision = "c6a209e741db"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("refresh_digest", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "last_used_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    op.create_table(
        "websocket_tickets",
        sa.Column("ticket_digest", sa.String(64), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_websocket_tickets_expires_at", "websocket_tickets", ["expires_at"])
    op.create_table(
        "auth_attempt_buckets",
        sa.Column("key_digest", sa.String(64), primary_key=True),
        sa.Column("scope", sa.String(40), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
    )
    op.create_index("ix_auth_bucket_window", "auth_attempt_buckets", ["window_started_at"])
    op.add_column("verification_codes", sa.Column("code_digest", sa.String(64)))
    # Old bearer tokens require fresh sign-in; outstanding plaintext challenges are
    # deliberately invalidated rather than silently treated as new-format digests.
    op.execute(
        "UPDATE verification_codes SET code_digest=repeat('0',64), is_used=true, used_at=now()"
    )
    op.alter_column("verification_codes", "code_digest", nullable=False)
    op.drop_column("verification_codes", "code")
    op.alter_column(
        "verification_codes", "telegram_id", type_=sa.BigInteger(), existing_type=sa.Integer()
    )


def downgrade():
    op.execute("UPDATE verification_codes SET is_used=true, used_at=now()")
    op.add_column(
        "verification_codes",
        sa.Column("code", sa.String(6), server_default="000000", nullable=False),
    )
    op.drop_column("verification_codes", "code_digest")
    # Keep Telegram ids as bigint: narrowing existing 64-bit ids would lose data.
    op.drop_table("auth_attempt_buckets")
    op.drop_table("websocket_tickets")
    op.drop_table("auth_sessions")
