from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2

revision: str = "4ad3fe2b3d32"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "service_zones",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "polygon",
            geoalchemy2.types.Geometry(
                geometry_type="POLYGON",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_service_zones_is_active"), "service_zones", ["is_active"], unique=False
    )
    op.create_index(
        op.f("ix_service_zones_name"), "service_zones", ["name"], unique=True
    )
    op.create_table(
        "users",
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("telegram_username", sa.String(length=100), nullable=True),
        sa.Column("telegram_mini_app_user_id", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("courier_status", sa.String(length=20), nullable=True),
        sa.Column("wallet_balance", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("total_orders", sa.Integer(), nullable=False),
        sa.Column("completed_orders", sa.Integer(), nullable=False),
        sa.Column("total_earnings", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("passport_number", sa.String(length=20), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(
        "idx_users_courier_status", "users", ["courier_status"], unique=False
    )
    op.create_index(
        "idx_users_role_active", "users", ["role", "is_active"], unique=False
    )
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=True)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.create_index(op.f("ix_users_telegram_id"), "users", ["telegram_id"], unique=True)
    op.create_index(
        op.f("ix_users_telegram_username"), "users", ["telegram_username"], unique=False
    )
    op.create_table(
        "addresses",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("full_address", sa.String(length=500), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=False),
        sa.Column("street", sa.String(length=200), nullable=False),
        sa.Column("house_number", sa.String(length=20), nullable=False),
        sa.Column("apartment", sa.String(length=20), nullable=True),
        sa.Column("entrance", sa.Integer(), nullable=True),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("intercom_code", sa.String(length=500), nullable=True),
        sa.Column("label", sa.String(length=20), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("yandex_geocoder_response", sa.String(), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_address_district", "addresses", ["district"], unique=False)
    op.create_index(
        "idx_user_default_address", "addresses", ["user_id", "is_default"], unique=False
    )
    op.create_table(
        "courier_shifts",
        sa.Column("courier_id", sa.UUID(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("orders_completed", sa.Integer(), nullable=False),
        sa.Column("orders_declined", sa.Integer(), nullable=False),
        sa.Column("total_earned", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "platform_fee_total", sa.Numeric(precision=10, scale=2), nullable=False
        ),
        sa.Column(
            "start_location_lat", sa.Numeric(precision=10, scale=8), nullable=True
        ),
        sa.Column(
            "start_location_lon", sa.Numeric(precision=11, scale=8), nullable=True
        ),
        sa.Column("end_location_lat", sa.Numeric(precision=10, scale=8), nullable=True),
        sa.Column("end_location_lon", sa.Numeric(precision=11, scale=8), nullable=True),
        sa.Column(
            "total_distance_km", sa.Numeric(precision=10, scale=2), nullable=False
        ),
        sa.Column("break_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("early_end_reason", sa.String(length=500), nullable=True),
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
        sa.ForeignKeyConstraint(["courier_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_courier_shift_courier_active",
        "courier_shifts",
        ["courier_id", "ended_at"],
        unique=False,
    )
    op.create_index(
        "idx_courier_shift_courier_id", "courier_shifts", ["courier_id"], unique=False
    )
    op.create_index(
        "idx_courier_shift_courier_started",
        "courier_shifts",
        ["courier_id", "started_at"],
        unique=False,
    )
    op.create_index(
        "idx_courier_shift_ended_at", "courier_shifts", ["ended_at"], unique=False
    )
    op.create_index(
        "idx_courier_shift_started_at", "courier_shifts", ["started_at"], unique=False
    )
    op.create_table(
        "subscriptions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("tier", sa.String(length=20), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("renewed_count", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        "idx_subscription_end_date", "subscriptions", ["end_date"], unique=False
    )
    op.create_index(
        "idx_subscription_is_active", "subscriptions", ["is_active"], unique=False
    )
    op.create_index(
        "idx_subscription_tier_active",
        "subscriptions",
        ["tier", "is_active"],
        unique=False,
    )
    op.create_index(
        "idx_subscription_user_id", "subscriptions", ["user_id"], unique=False
    )
    op.create_table(
        "orders",
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("courier_id", sa.UUID(), nullable=True),
        sa.Column("pickup_address_id", sa.UUID(), nullable=False),
        sa.Column("garbage_type", sa.String(length=20), nullable=False),
        sa.Column("number_of_bags", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "price_before_discount", sa.Numeric(precision=10, scale=2), nullable=False
        ),
        sa.Column("discount_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("final_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("subscription_tier_used", sa.String(length=20), nullable=True),
        sa.Column("courier_payout", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("platform_fee", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("distance_km", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("scheduled_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=500), nullable=True),
        sa.Column("cancelled_by_id", sa.UUID(), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["cancelled_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["courier_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["pickup_address_id"], ["addresses.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_order_cancelled_by_id", "orders", ["cancelled_by_id"], unique=False
    )
    op.create_index(
        "idx_order_client_created", "orders", ["client_id", "created_at"], unique=False
    )
    op.create_index("idx_order_client_id", "orders", ["client_id"], unique=False)
    op.create_index("idx_order_completed_at", "orders", ["completed_at"], unique=False)
    op.create_index("idx_order_courier_id", "orders", ["courier_id"], unique=False)
    op.create_index(
        "idx_order_courier_status", "orders", ["courier_id", "status"], unique=False
    )
    op.create_index(
        "idx_order_pickup_address_id", "orders", ["pickup_address_id"], unique=False
    )
    op.create_index(
        "idx_order_scheduled_time", "orders", ["scheduled_time"], unique=False
    )
    op.create_index("idx_order_status", "orders", ["status"], unique=False)
    op.create_table(
        "notifications",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=True),
        sa.Column("notification_type", sa.String(length=30), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("telegram_message_id", sa.String(length=100), nullable=True),
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
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_notification_channel", "notifications", ["channel"], unique=False
    )
    op.create_index(
        "idx_notification_is_read", "notifications", ["is_read"], unique=False
    )
    op.create_index(
        "idx_notification_order_id", "notifications", ["order_id"], unique=False
    )
    op.create_index(
        "idx_notification_sent_at", "notifications", ["sent_at"], unique=False
    )
    op.create_index(
        "idx_notification_type", "notifications", ["notification_type"], unique=False
    )
    op.create_index(
        "idx_notification_user_created",
        "notifications",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_notification_user_id", "notifications", ["user_id"], unique=False
    )
    op.create_index(
        "idx_notification_user_read",
        "notifications",
        ["user_id", "is_read"],
        unique=False,
    )
    op.create_table(
        "order_queue",
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("courier_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decline_reason", sa.String(length=30), nullable=True),
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
        sa.ForeignKeyConstraint(["courier_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "courier_id", name="uq_order_courier"),
    )
    op.create_index(
        "idx_order_queue_courier_id", "order_queue", ["courier_id"], unique=False
    )
    op.create_index(
        "idx_order_queue_courier_status",
        "order_queue",
        ["courier_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_order_queue_expires_at", "order_queue", ["expires_at"], unique=False
    )
    op.create_index(
        "idx_order_queue_order_id", "order_queue", ["order_id"], unique=False
    )
    op.create_index(
        "idx_order_queue_order_priority",
        "order_queue",
        ["order_id", "priority"],
        unique=False,
    )
    op.create_index("idx_order_queue_status", "order_queue", ["status"], unique=False)
    op.create_table(
        "payments",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=True),
        sa.Column("subscription_id", sa.UUID(), nullable=True),
        sa.Column("refund_for_payment_id", sa.UUID(), nullable=True),
        sa.Column("payment_type", sa.String(length=30), nullable=False),
        sa.Column("payment_method", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("yookassa_payment_id", sa.String(length=100), nullable=True),
        sa.Column("yookassa_response", sa.Text(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["refund_for_payment_id"], ["payments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("yookassa_payment_id"),
    )
    op.create_index("idx_payment_order_id", "payments", ["order_id"], unique=False)
    op.create_index(
        "idx_payment_refund_for", "payments", ["refund_for_payment_id"], unique=False
    )
    op.create_index("idx_payment_status", "payments", ["status"], unique=False)
    op.create_index(
        "idx_payment_subscription_id", "payments", ["subscription_id"], unique=False
    )
    op.create_index("idx_payment_type", "payments", ["payment_type"], unique=False)
    op.create_index("idx_payment_user_id", "payments", ["user_id"], unique=False)
    op.create_index(
        "idx_payment_user_status", "payments", ["user_id", "status"], unique=False
    )
    op.create_index(
        "idx_payment_user_type", "payments", ["user_id", "payment_type"], unique=False
    )
    op.create_index(
        "idx_payment_yookassa_id", "payments", ["yookassa_payment_id"], unique=False
    )
    op.create_table(
        "reviews",
        sa.Column("reviewer_id", sa.UUID(), nullable=False),
        sa.Column("reviewee_id", sa.UUID(), nullable=False),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("moderated_by_id", sa.UUID(), nullable=True),
        sa.Column("reviewer_role", sa.String(length=10), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False),
        sa.Column("moderation_note", sa.Text(), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
        sa.ForeignKeyConstraint(["moderated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "reviewer_id", name="uq_order_reviewer"),
    )
    op.create_index("idx_review_is_visible", "reviews", ["is_visible"], unique=False)
    op.create_index(
        "idx_review_moderated_by", "reviews", ["moderated_by_id"], unique=False
    )
    op.create_index("idx_review_order_id", "reviews", ["order_id"], unique=False)
    op.create_index("idx_review_rating", "reviews", ["rating"], unique=False)
    op.create_index("idx_review_reviewee_id", "reviews", ["reviewee_id"], unique=False)
    op.create_index(
        "idx_review_reviewee_rating", "reviews", ["reviewee_id", "rating"], unique=False
    )
    op.create_index(
        "idx_review_reviewee_visible",
        "reviews",
        ["reviewee_id", "is_visible"],
        unique=False,
    )
    op.create_index("idx_review_reviewer_id", "reviews", ["reviewer_id"], unique=False)
    op.create_index(
        "idx_review_reviewer_role", "reviews", ["reviewer_role"], unique=False
    )
    op.create_table(
        "wallet_transactions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("payment_id", sa.UUID(), nullable=True),
        sa.Column("order_id", sa.UUID(), nullable=True),
        sa.Column("subscription_id", sa.UUID(), nullable=True),
        sa.Column("admin_id", sa.UUID(), nullable=True),
        sa.Column("transaction_type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("balance_before", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("balance_after", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("withdrawal_details", sa.Text(), nullable=True),
        sa.Column("admin_note", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_wallet_tx_admin_created",
        "wallet_transactions",
        ["admin_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_wallet_tx_admin_id", "wallet_transactions", ["admin_id"], unique=False
    )
    op.create_index(
        "idx_wallet_tx_created_at", "wallet_transactions", ["created_at"], unique=False
    )
    op.create_index(
        "idx_wallet_tx_order_id", "wallet_transactions", ["order_id"], unique=False
    )
    op.create_index(
        "idx_wallet_tx_payment_id", "wallet_transactions", ["payment_id"], unique=False
    )
    op.create_index(
        "idx_wallet_tx_subscription_id",
        "wallet_transactions",
        ["subscription_id"],
        unique=False,
    )
    op.create_index(
        "idx_wallet_tx_type", "wallet_transactions", ["transaction_type"], unique=False
    )
    op.create_index(
        "idx_wallet_tx_user_created",
        "wallet_transactions",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_wallet_tx_user_id", "wallet_transactions", ["user_id"], unique=False
    )
    op.create_index(
        "idx_wallet_tx_user_type",
        "wallet_transactions",
        ["user_id", "transaction_type"],
        unique=False,
    )

def downgrade() -> None:
    op.drop_index("idx_wallet_tx_user_type", table_name="wallet_transactions")
    op.drop_index("idx_wallet_tx_user_id", table_name="wallet_transactions")
    op.drop_index("idx_wallet_tx_user_created", table_name="wallet_transactions")
    op.drop_index("idx_wallet_tx_type", table_name="wallet_transactions")
    op.drop_index("idx_wallet_tx_subscription_id", table_name="wallet_transactions")
    op.drop_index("idx_wallet_tx_payment_id", table_name="wallet_transactions")
    op.drop_index("idx_wallet_tx_order_id", table_name="wallet_transactions")
    op.drop_index("idx_wallet_tx_created_at", table_name="wallet_transactions")
    op.drop_index("idx_wallet_tx_admin_id", table_name="wallet_transactions")
    op.drop_index("idx_wallet_tx_admin_created", table_name="wallet_transactions")
    op.drop_table("wallet_transactions")
    op.drop_index("idx_review_reviewer_role", table_name="reviews")
    op.drop_index("idx_review_reviewer_id", table_name="reviews")
    op.drop_index("idx_review_reviewee_visible", table_name="reviews")
    op.drop_index("idx_review_reviewee_rating", table_name="reviews")
    op.drop_index("idx_review_reviewee_id", table_name="reviews")
    op.drop_index("idx_review_rating", table_name="reviews")
    op.drop_index("idx_review_order_id", table_name="reviews")
    op.drop_index("idx_review_moderated_by", table_name="reviews")
    op.drop_index("idx_review_is_visible", table_name="reviews")
    op.drop_table("reviews")
    op.drop_index("idx_payment_yookassa_id", table_name="payments")
    op.drop_index("idx_payment_user_type", table_name="payments")
    op.drop_index("idx_payment_user_status", table_name="payments")
    op.drop_index("idx_payment_user_id", table_name="payments")
    op.drop_index("idx_payment_type", table_name="payments")
    op.drop_index("idx_payment_subscription_id", table_name="payments")
    op.drop_index("idx_payment_status", table_name="payments")
    op.drop_index("idx_payment_refund_for", table_name="payments")
    op.drop_index("idx_payment_order_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("idx_order_queue_status", table_name="order_queue")
    op.drop_index("idx_order_queue_order_priority", table_name="order_queue")
    op.drop_index("idx_order_queue_order_id", table_name="order_queue")
    op.drop_index("idx_order_queue_expires_at", table_name="order_queue")
    op.drop_index("idx_order_queue_courier_status", table_name="order_queue")
    op.drop_index("idx_order_queue_courier_id", table_name="order_queue")
    op.drop_table("order_queue")
    op.drop_index("idx_notification_user_read", table_name="notifications")
    op.drop_index("idx_notification_user_id", table_name="notifications")
    op.drop_index("idx_notification_user_created", table_name="notifications")
    op.drop_index("idx_notification_type", table_name="notifications")
    op.drop_index("idx_notification_sent_at", table_name="notifications")
    op.drop_index("idx_notification_order_id", table_name="notifications")
    op.drop_index("idx_notification_is_read", table_name="notifications")
    op.drop_index("idx_notification_channel", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("idx_order_status", table_name="orders")
    op.drop_index("idx_order_scheduled_time", table_name="orders")
    op.drop_index("idx_order_pickup_address_id", table_name="orders")
    op.drop_index("idx_order_courier_status", table_name="orders")
    op.drop_index("idx_order_courier_id", table_name="orders")
    op.drop_index("idx_order_completed_at", table_name="orders")
    op.drop_index("idx_order_client_id", table_name="orders")
    op.drop_index("idx_order_client_created", table_name="orders")
    op.drop_index("idx_order_cancelled_by_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("idx_subscription_user_id", table_name="subscriptions")
    op.drop_index("idx_subscription_tier_active", table_name="subscriptions")
    op.drop_index("idx_subscription_is_active", table_name="subscriptions")
    op.drop_index("idx_subscription_end_date", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("idx_courier_shift_started_at", table_name="courier_shifts")
    op.drop_index("idx_courier_shift_ended_at", table_name="courier_shifts")
    op.drop_index("idx_courier_shift_courier_started", table_name="courier_shifts")
    op.drop_index("idx_courier_shift_courier_id", table_name="courier_shifts")
    op.drop_index("idx_courier_shift_courier_active", table_name="courier_shifts")
    op.drop_table("courier_shifts")
    op.drop_index("idx_user_default_address", table_name="addresses")
    op.drop_index(
        "idx_addresses_location", table_name="addresses", postgresql_using="gist"
    )
    op.drop_index(
        "idx_address_location", table_name="addresses", postgresql_using="gist"
    )
    op.drop_index("idx_address_district", table_name="addresses")
    op.drop_table("addresses")
    op.drop_index(op.f("ix_users_telegram_username"), table_name="users")
    op.drop_index(op.f("ix_users_telegram_id"), table_name="users")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.drop_index("idx_users_role_active", table_name="users")
    op.drop_index("idx_users_courier_status", table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_service_zones_name"), table_name="service_zones")
    op.drop_index(op.f("ix_service_zones_is_active"), table_name="service_zones")
    op.drop_index(
        "idx_service_zones_polygon", table_name="service_zones", postgresql_using="gist"
    )
    op.drop_index(
        "idx_service_zone_polygon", table_name="service_zones", postgresql_using="gist"
    )
    op.drop_table("service_zones")
