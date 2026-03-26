from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "ac023023a5c3"
down_revision: Union[str, Sequence[str], None] = "4ad3fe2b3d32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "verification_codes",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=6), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("telegram_id", sa.Integer(), nullable=True),
        sa.Column("purpose", sa.String(length=50), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_verification_codes_email"),
        "verification_codes",
        ["email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_verification_codes_telegram_id"),
        "verification_codes",
        ["telegram_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_verification_codes_user_id"),
        "verification_codes",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "idx_address_location",
        "addresses",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index(
        "idx_service_zone_polygon",
        "service_zones",
        ["polygon"],
        unique=False,
        postgresql_using="gist",
    )
    op.add_column(
        "subscriptions", sa.Column("auto_renew_enabled", sa.Boolean(), nullable=False)
    )
    op.add_column(
        "subscriptions",
        sa.Column("yookassa_payment_method_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("next_billing_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "subscriptions", sa.Column("last_payment_id", sa.UUID(), nullable=True)
    )
    op.create_index(
        "idx_subscription_auto_renew",
        "subscriptions",
        ["auto_renew_enabled", "next_billing_date"],
        unique=False,
    )
    op.create_foreign_key(
        None,
        "subscriptions",
        "payments",
        ["last_payment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("users", sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade() -> None:
    op.drop_column("users", "is_email_verified")
    op.drop_constraint(None, "subscriptions", type_="foreignkey")
    op.drop_index("idx_subscription_auto_renew", table_name="subscriptions")
    op.drop_column("subscriptions", "last_payment_id")
    op.drop_column("subscriptions", "next_billing_date")
    op.drop_column("subscriptions", "yookassa_payment_method_id")
    op.drop_column("subscriptions", "auto_renew_enabled")
    op.drop_index(
        "idx_service_zone_polygon", table_name="service_zones", postgresql_using="gist"
    )
    op.drop_index(
        "idx_address_location", table_name="addresses", postgresql_using="gist"
    )
    op.drop_index(
        op.f("ix_verification_codes_user_id"), table_name="verification_codes"
    )
    op.drop_index(
        op.f("ix_verification_codes_telegram_id"), table_name="verification_codes"
    )
    op.drop_index(op.f("ix_verification_codes_email"), table_name="verification_codes")
    op.drop_table("verification_codes")
